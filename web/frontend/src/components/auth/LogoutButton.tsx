import { useAuth0 } from '@auth0/auth0-react';

export function LogoutButton() {
  const { logout } = useAuth0();
  return (
    <button
      onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
    >
      Sign Out
    </button>
  )
}
