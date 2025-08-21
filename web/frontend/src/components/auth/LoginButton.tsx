import { useAuth0 } from '@auth0/auth0-react';

export function LoginButton() {
  const { loginWithRedirect } = useAuth0();
  return (
    <button
      onClick={() => loginWithRedirect()}
      className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
    >
      Sign In
    </button>
  )
}
