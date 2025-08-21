'use client'

export function LoginButton() {
  return (
    <a
      href="/api/auth/login"
      className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
    >
      Sign In
    </a>
  )
}
