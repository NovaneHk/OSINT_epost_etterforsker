import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  // A list of all locales that are supported
  locales: ['nb', 'en'],

  // Used when no locale matches
  defaultLocale: 'nb',

  // Always use locale prefix
  localePrefix: 'as-needed'
});

export const config = {
  // Match only internationalized pathnames
  matcher: ['/', '/(nb|en)/:path*']
};