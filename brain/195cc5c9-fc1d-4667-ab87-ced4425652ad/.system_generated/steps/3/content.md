Title: Carbon Tech

Source: http://localhost:5173

---

<!doctype html>
<html lang="en">
  <head>
    <script type="module">import { injectIntoGlobalHook } from "/@react-refresh";
injectIntoGlobalHook(window);
window.$RefreshReg$ = () => {};
window.$RefreshSig$ = () => (type) => type;</script>

    <script type="module" src="/@vite/client"></script>

    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/carbon_tech.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Carbon Tech</title>
    <script>
      // Suppress React DevTools download console hint in development
      if (typeof window !== "undefined") {
        const _origInfo = console.info;
        console.info = function (...args) {
          if (typeof args[0] === "string" && args[0].includes("React DevTools")) return;
          _origInfo.apply(console, args);
        };
      }
      (function() {
        var redirect = sessionStorage.redirect;
        delete sessionStorage.redirect;
        if (redirect && redirect !== location.pathname) {
          history.replaceState(null, null, redirect);
        }
      })();
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx?t=1790150920731"></script>
  </body>
</html>


