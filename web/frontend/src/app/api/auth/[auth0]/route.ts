import { handleAuth, handleLogin, handleLogout, handleCallback, handleProfile } from '@auth0/nextjs-auth0'

export const GET = handleAuth({
  login: handleLogin({
    returnTo: '/'
  }),
  logout: handleLogout({
    returnTo: '/'
  }),
  callback: handleCallback(),
  profile: handleProfile()
})
