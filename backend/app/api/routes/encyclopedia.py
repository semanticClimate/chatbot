from fastapi import APIRouter, FastAPI, HTTPException, Request

from fastapi.responses import HTMLResponse
from pathlib import Path

from backend.app.config.settings import AppSettings


from backend.app.rag.encyclopedia_document import (

    build_encyclopedia_entry_document,

    build_encyclopedia_placeholder_document,

    normalize_entry_id,

    prepared_encyclopedia_path,

)


router = APIRouter()



def _cached_encyclopedia_placeholder(app: FastAPI) -> str:
    if getattr(app.state, "_encyclopedia_placeholder_html", None) is None:
        app.state._encyclopedia_placeholder_html = build_encyclopedia_placeholder_document()
    return app.state._encyclopedia_placeholder_html



@router.get("/encyclopedia/empty", response_class=HTMLResponse)
def encyclopedia_empty(request: Request) -> HTMLResponse:
    """Placeholder document for the encyclopedia iframe before a term is chosen."""
    return HTMLResponse(content=_cached_encyclopedia_placeholder(request.app))


@router.get("/encyclopedia/entry/{entry_id}", response_class=HTMLResponse)
def encyclopedia_entry(entry_id: str, request: Request) -> HTMLResponse:
    """Single CA encyclopedia entry for the browser client iframe."""
    s: AppSettings = request.app.state.settings
    enc = prepared_encyclopedia_path(s)
    print("ENC PATH:", enc)
    # enc = html_file = Path("D:/Aleena/Programming/Internship/#semanticclimate/Chatbot_og_refactored/Chatbot_V1/data/encyclopedia/source/CA_encyclopedia_new.html")
    print("EXISTS:", enc.exists())
    print("IS FILE:", enc.is_file())
    # D:\Aleena\Programming\Internship\#semanticclimate\Chatbot_og_refactored\Chatbot_V1\data\encyclopedia\source
    if not enc.is_file():
        raise HTTPException(status_code=503, detail="Encyclopedia HTML not available")
    try:
        wid = normalize_entry_id(entry_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        html = build_encyclopedia_entry_document(wid, s)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return HTMLResponse(content=html)


@router.get("/proxy", response_class=HTMLResponse)
async def proxy_external(url: str, request: Request) -> HTMLResponse:
    """Proxy external Wikipedia/Wikidata requests to bypass iframe restrictions."""
    import httpx
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if not ("wikipedia.org" in domain or "wikidata.org" in domain):
        raise HTTPException(status_code=400, detail="Only Wikipedia and Wikidata links can be proxied.")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            content = response.text
            
            # Insert a base tag so relative assets resolve to the original site
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            base_tag = f'\n<base href="{base_url}/">\n'
            if "<head>" in content:
                content = content.replace("<head>", f"<head>{base_tag}", 1)
            elif "<HEAD>" in content:
                content = content.replace("<HEAD>", f"<HEAD>{base_tag}", 1)
            else:
                content = f"{base_tag}{content}"
            
            # Inject link interception script inside the proxied page to rewrite sub-links
            script_tag = """
<script>
(function() {
  document.addEventListener("click", function(e) {
    var anchor = e.target.closest("a");
    if (!anchor) return;
    var href = anchor.getAttribute("href");
    if (!href) return;
    var absoluteUrl = new URL(href, document.baseURI).href;
    if (absoluteUrl.indexOf("wikipedia.org") >= 0 || absoluteUrl.indexOf("wikidata.org") >= 0) {
      e.preventDefault();
      window.location.href = "/proxy?url=" + encodeURIComponent(absoluteUrl);
    }
  });
})();
</script>
"""
            if "</body>" in content:
                content = content.replace("</body>", f"{script_tag}</body>", 1)
            elif "</BODY>" in content:
                content = content.replace("</BODY>", f"{script_tag}</BODY>", 1)
            else:
                content = f"{content}{script_tag}"
                
            return HTMLResponse(content=content, status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch external resource: {str(e)}")

