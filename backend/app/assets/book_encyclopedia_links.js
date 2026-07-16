/**
 * Intercept in-book encyclopedia links; ask the host web client to open the entry panel.
 */
(function () {
  function entryIdFromLink(anchor) {
    var id = anchor.getAttribute("data-entry-id");
    if (id) return id.trim();
    var href = anchor.getAttribute("href") || "";
    var hash = "";
    var i = href.indexOf("#");
    if (i >= 0) hash = href.slice(i + 1);
    if (hash.toLowerCase().indexOf("entry-") === 0) return hash.slice(6);
    return hash;
  }

  document.addEventListener(
    "click",
    function (e) {
      var anchor = e.target.closest("a.ca-encyclopedia-link");
      if (!anchor) return;
      var entryId = entryIdFromLink(anchor);
      if (!entryId) return;
      e.preventDefault();
      if (window.parent && window.parent !== window) {
        window.parent.postMessage(
          { type: "ca-encyclopedia-open", entry_id: entryId },
          "*"
        );
      }
    },
    true
  );
})();
