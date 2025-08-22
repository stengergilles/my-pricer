# Session Summary: Frontend Refactoring & Auth0 Integration

This session involved a significant refactoring of the frontend from Tailwind CSS to Material-UI (MUI) and extensive troubleshooting and correction of Auth0 integration for both the frontend and backend.

## 1. Frontend Refactoring to Material-UI (MUI)

**Reasoning:**
The original frontend used Tailwind CSS classes, but due to platform limitations (Tailwind requiring Rust, which was problematic), the decision was made to refactor to Material-UI, which was already a dependency.

**Key Changes:**

*   **Core Components Refactored:**
    *   `web/frontend/src/App.js`: The main application layout, header, navigation, and routing were completely rewritten using MUI `Box`, `Container`, `AppBar`, `Toolbar`, `Button`, `Tabs`, and `Tab` components. All original Tailwind `className` attributes were replaced with MUI's `sx` prop for styling.
    *   `web/frontend/src/components/auth/LoginButton.tsx` & `LogoutButton.tsx`: Refactored to use MUI `Button` components with `variant` and `color` props.
    *   `web/frontend/src/components/HealthStatus.tsx`: Refactored to use MUI `Box`, `Typography`, `CircularProgress`, and `FiberManualRecordIcon` for status display, replacing custom Tailwind-styled `div`s and `span`s.
    *   `web/frontend/src/components/CryptoAnalysis.tsx` & `web/frontend/src/components/BacktestRunner.tsx`: These complex components (forms and result displays) were refactored section by section, replacing HTML elements with appropriate MUI components like `TextField`, `Select`, `MenuItem`, `FormControl`, `InputLabel`, `Grid`, `Paper`, `Alert`, `Checkbox`, `FormControlLabel`, and `CircularProgress`. Custom styled components (`StyledPaper`, `ResultBox`) were introduced using MUI's `styled` utility for consistent theming.
*   **CSS Cleanup:**
    *   All original CSS files (`web/frontend/src/App.css`, `web/frontend/src/index.css`, `web/frontend/src/globals.css`) were removed as their styling was replaced by MUI's theming and component-level styling.
*   **MUI Theming Integration:**
    *   `web/frontend/src/index.js`: The entire React application was wrapped with `ThemeProvider` from `@mui/material/styles`, providing a global theme context. A basic `theme` object was created using `createTheme` to define palette colors and typography settings (e.g., `fontWeightMedium`), resolving runtime errors related to theme access. `CssBaseline` was also added for consistent baseline styles across browsers.

## 2. Auth0 Integration & Troubleshooting

The Auth0 setup required several corrections across both frontend and backend to ensure proper token exchange and validation.

### Frontend Configuration (`web/frontend/.env.local`):

To enable Auth0 authentication in the frontend, ensure your `web/frontend/.env.local` file (located in `my-pricer/web/frontend/`) contains the following variables, populated with your Auth0 application and API details:

```dotenv
REACT_APP_AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN_FROM_SPA_APP
REACT_APP_AUTH0_CLIENT_ID=YOUR_AUTH0_CLIENT_ID_FROM_SPA_APP
REACT_APP_AUTH0_AUDIENCE=YOUR_AUTH0_API_IDENTIFIER
```

*   **`YOUR_AUTH0_DOMAIN_FROM_SPA_APP`**: Your Auth0 tenant domain (e.g., `dev-xxxxxxxx.eu.auth0.com`). Find this in your Auth0 Dashboard under **Applications -> (Your SPA Application) -> Domain**.
*   **`YOUR_AUTH0_CLIENT_ID_FROM_SPA_APP`**: The Client ID for your Auth0 Single Page Application. Find this in your Auth0 Dashboard under **Applications -> (Your SPA Application) -> Client ID**.
*   **`YOUR_AUTH0_API_IDENTIFIER`**: This is the unique identifier for your Auth0 API. Find this in your Auth0 Dashboard under **Applications -> APIs -> (Your API Name) -> Identifier**. This is crucial for the frontend to request an Access Token valid for your backend.

### Frontend Code Adjustments:

*   **`web/frontend/src/index.js`**: The `Auth0Provider` component was updated to include the `audience` parameter in its `authorizationParams`. This ensures that the frontend requests an Access Token specifically for your backend API.
    ```javascript
    <Auth0Provider
      domain={process.env.REACT_APP_AUTH0_DOMAIN}
      clientId={process.env.REACT_APP_AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: process.env.REACT_APP_AUTH0_AUDIENCE, // Crucial for API access
      }}
    >
      <App />
    </Auth0Provider>
    ```
*   **`web/frontend/src/utils/api.ts`**: The `ApiClient` was modified to accept a `getAccessToken` function in its constructor. This function is used in an Axios request interceptor to dynamically inject the Auth0 Access Token into API requests.
*   **`web/frontend/src/hooks/useApiClient.ts` (New File):** A custom React hook was created to leverage `useAuth0().getAccessTokenSilently()` and provide an `ApiClient` instance pre-configured with the token retrieval logic.
*   **Component Updates:** All components (`CryptoAnalysis.tsx`, `BacktestRunner.tsx`, `HealthStatus.tsx`) that make API calls were updated to use the new `useApiClient` hook instead of directly importing `apiClient`.
*   **Import Path Fixes:** Explicit `.ts` extensions were added to import paths (e.g., `../hooks/useApiClient.ts`) to resolve "Module not found" errors during compilation.

### Backend Configuration (`web/backend/.env`):

To enable Auth0 token validation in the backend, ensure your `web/backend/.env` file (located in `my-pricer/web/backend/`) contains the following variables:

```dotenv
AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN_FROM_SPA_APP
AUTH0_API_AUDIENCE=YOUR_AUTH0_API_IDENTIFIER
AUTH0_CLIENT_ID=YOUR_AUTH0_API_CLIENT_ID
AUTH0_CLIENT_SECRET=YOUR_AUTH0_API_CLIENT_SECRET
```

*   **`AUTH0_DOMAIN`**: Same as `REACT_APP_AUTH0_DOMAIN` from your SPA app.
*   **`AUTH0_API_AUDIENCE`**: Same as `YOUR_AUTH0_API_IDENTIFIER` from your API.
*   **`AUTH0_CLIENT_ID`**: The Client ID for your Auth0 API. Find this in your Auth0 Dashboard under **Applications -> APIs -> (Your API Name) -> Client ID**.
*   **`AUTH0_CLIENT_SECRET`**: The Client Secret for your Auth0 API. Find this in your Auth0 Dashboard under **Applications -> APIs -> (Your API Name) -> Client Secret**. **This is a sensitive value and must be kept secret.**

### Backend Code Adjustments:

*   **`web/backend/auth/middleware.py`**:
    *   The error handling in the `requires_auth` decorator was adjusted to re-raise `AuthError` exceptions, allowing Flask-RESTful's error handlers to format responses correctly, resolving `TypeError: Object of type Response is not JSON serializable`.
    *   The `verify_decode_jwt` function was updated to correctly handle and log different token validation failures.
    *   **Crucially, the backend was configured to expect a *signed* Access Token (JWS) and not an *encrypted* one (JWE).** The previous `invalid_header` error with `alg: 'dir'` indicated an encrypted token was being sent. This was resolved by ensuring the `audience` parameter was correctly passed from the frontend, prompting Auth0 to issue the correct type of token.
*   **Logging:** Debug logging was temporarily enabled in `web/backend/auth/middleware.py` and `web/backend/app.py` to aid in troubleshooting, and then reverted to `INFO` level.

### General Troubleshooting Tips:

*   **Clear Browser Data:** Always clear browser cookies and local storage for both your frontend application and your Auth0 domain when troubleshooting authentication issues.
*   **Auth0 Dashboard Verification:** Double-check all URLs (Callback, Web Origins, Logout) in your Auth0 SPA application settings and ensure your API Identifier matches exactly.
*   **Backend Server Restart:** Always restart your backend server after making changes to its code or `.env` file.
