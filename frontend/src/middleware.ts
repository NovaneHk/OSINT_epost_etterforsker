import { NextResponse, NextRequest } from 'next/server';
import createIntlMiddleware from 'next-intl/middleware';

// Protected routes that require authentication
const protectedRoutes = [
    '/analytics',
    '/campaigns',
    '/dashboard',
    '/exports',
    '/investigation',
    '/investigations',
    '/leads',
    '/monitoring',
    '/new-investigation',
    '/playbooks',
    '/runs',
    '/settings',
    '/sources',
];

// Create internationalization middleware
const intlMiddleware = createIntlMiddleware({
    locales: ['nb', 'en'],
    defaultLocale: 'nb',
    localePrefix: 'as-needed'
});

export async function middleware(request: NextRequest) {
    const token = request.cookies.get('token')?.value;
    const currentPath = request.nextUrl.pathname;
    const normalizedPath = currentPath.replace(/^\/(nb|en)(?=\/|$)/, '') || '/';

    // Check if we're on a protected route
    const isProtectedRoute = protectedRoutes.some(route => 
        normalizedPath.startsWith(route)
    );

    const isProtectedRoot = normalizedPath === '/';

    if ((isProtectedRoute || isProtectedRoot) && !token) {
        // Redirect to login page if no token is found
        const loginUrl = new URL('/login', request.url);
        loginUrl.searchParams.set('redirect', currentPath);
        return NextResponse.redirect(loginUrl);
    }

    // Apply internationalization middleware if we pass authentication
    return intlMiddleware(request);
}

export const config = {
    matcher: [
        // Match all routes for internationalization
        '/',
        '/(nb|en)/:path*',
        // Match protected routes for authentication
        '/analytics/:path*',
        '/campaigns/:path*',
        '/dashboard/:path*',
        '/exports/:path*',
        '/investigation/:path*',
        '/investigations/:path*',
        '/leads/:path*',
        '/monitoring/:path*',
        '/new-investigation/:path*',
        '/playbooks/:path*',
        '/runs/:path*',
        '/settings/:path*',
        '/sources/:path*',
    ]
};