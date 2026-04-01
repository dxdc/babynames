import { d as derived, w as writable } from "./index2.js";
const LEVEL_PRIORITY = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3
};
let minLevel = "debug";
function emit(level, component, msg, data) {
  if (LEVEL_PRIORITY[level] < LEVEL_PRIORITY[minLevel]) return;
  const entry = {
    ts: (/* @__PURE__ */ new Date()).toISOString(),
    level,
    component,
    msg
  };
  if (data !== void 0) entry.data = data;
  const tag = `[BabyNames:${component}]`;
  const json = JSON.stringify(entry);
  switch (level) {
    case "debug":
      console.debug(tag, json);
      break;
    case "info":
      console.info(tag, json);
      break;
    case "warn":
      console.warn(tag, json);
      break;
    case "error":
      console.error(tag, json);
      break;
  }
}
function logger(component) {
  return {
    debug: (msg, data) => emit("debug", component, msg, data),
    info: (msg, data) => emit("info", component, msg, data),
    warn: (msg, data) => emit("warn", component, msg, data),
    error: (msg, data) => emit("error", component, msg, data)
  };
}
const log = logger("Auth");
const AUTHENTIK_URL = "";
const CLIENT_ID = "";
function createAuthStore() {
  const initial = { user: null, token: null, loading: true, error: null };
  const { subscribe, set, update } = writable(initial);
  function persist(state) {
  }
  return {
    subscribe,
    login() {
      {
        log.warn("Authentik not configured — using dev mode");
        const devState = {
          user: { sub: "dev-user", name: "Developer", email: "dev@localhost" },
          token: "dev-token",
          loading: false,
          error: null
        };
        set(devState);
        return;
      }
    },
    async handleCallback(code) {
      update((s) => ({ ...s, loading: true, error: null }));
      log.info("handling auth callback");
      try {
        const redirectUri = `${window.location.origin}/auth/callback`;
        const resp = await fetch(`${AUTHENTIK_URL}/application/o/token/`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            grant_type: "authorization_code",
            code,
            client_id: CLIENT_ID,
            redirect_uri: redirectUri
          })
        });
        if (!resp.ok) {
          throw new Error(`Token exchange failed: ${resp.status}`);
        }
        const data = await resp.json();
        const token = data.access_token;
        const userResp = await fetch(`${AUTHENTIK_URL}/application/o/userinfo/`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const userInfo = await userResp.json();
        const newState = {
          user: { sub: userInfo.sub, name: userInfo.name || userInfo.preferred_username, email: userInfo.email },
          token,
          loading: false,
          error: null
        };
        set(newState);
        persist(newState);
        log.info("logged in", { user: newState.user?.name });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Login failed";
        log.error("auth callback failed", { error: msg });
        update((s) => ({ ...s, loading: false, error: msg }));
      }
    },
    logout() {
      set({ user: null, token: null, loading: false, error: null });
      log.info("logged out");
    },
    getToken() {
      let token = null;
      subscribe((s) => {
        token = s.token;
      })();
      return token;
    }
  };
}
const auth = createAuthStore();
const isAuthenticated = derived(auth, ($auth) => $auth.user !== null);
const currentUser = derived(auth, ($auth) => $auth.user);
export {
  auth as a,
  currentUser as c,
  isAuthenticated as i,
  logger as l
};
