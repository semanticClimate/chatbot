"""FastAPI entrypoint as a sibling package to `climate_streamlit`."""

from climate_streamlit.api_server import app


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "fastapi_app.main:app",
        host=os.environ.get("CLIMATE_API_HOST", "0.0.0.0"),
        port=int(os.environ.get("CLIMATE_API_PORT", "8800")),
        reload=False,
    )
