/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  // Experimental features
  experimental: {
    // Server components logging
    serverComponentsExternalPackages: [],
    // Optimize bundle size
    optimizeCss: true,
  },

  // Compiler options
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },

  // Image optimization
  images: {
    domains: ['localhost', 'api.osint-leads.com'],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },

  // Headers for security and performance
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // Security headers
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          // Performance headers
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
        ],
      },
      {
        source: '/api/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, must-revalidate',
          },
        ],
      },
      {
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: '/',
        permanent: false,
        has: [
          {
            type: 'cookie',
            key: 'auth-token',
            value: undefined,
          },
        ],
      },
    ];
  },

  // Rewrites for API proxy
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },


  // Webpack configuration
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Production optimizations
    if (!dev) {
      // Split chunks optimization
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: false,
          vendors: false,
          // Vendor chunk
          vendor: {
            name: 'vendor',
            chunks: 'all',
            test: /node_modules/,
            priority: 20,
          },
          // Common chunk
          common: {
            name: 'common',
            minChunks: 2,
            chunks: 'all',
            priority: 10,
            reuseExistingChunk: true,
            enforce: true,
          },
          // React chunk
          react: {
            name: 'react',
            chunks: 'all',
            test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
            priority: 30,
          },
          // UI components chunk
          ui: {
            name: 'ui',
            chunks: 'all',
            test: /[\\/]src[\\/]components[\\/]ui[\\/]/,
            priority: 25,
          },
        },
      };

      // Tree shaking optimization
      config.optimization.usedExports = true;
      config.optimization.sideEffects = false;
    }

    // Bundle analysis
    if (process.env.ANALYZE === 'true') {
      const BundleAnalyzerPlugin = require('@next/bundle-analyzer')({
        enabled: true,
      });
      config.plugins.push(new BundleAnalyzerPlugin());
    }

    // Performance optimizations
    config.resolve.alias = {
      ...config.resolve.alias,
      // Lighter alternatives
      'date-fns': 'date-fns/esm',
    };

    return config;
  },

  // Environment variables
  env: {
    BUILD_ID: process.env.BUILD_ID || 'development',
    BUILD_TIME: new Date().toISOString(),
  },

  // Performance monitoring
  onDemandEntries: {
    // Period (in ms) where the server will keep pages in the buffer
    maxInactiveAge: 25 * 1000,
    // Number of pages that should be kept simultaneously without being disposed
    pagesBufferLength: 2,
  },

  // Compression
  compress: true,

  // PoweredBy header
  poweredByHeader: false,

  // Generate ETags
  generateEtags: true,

  // HTTP Keep Alive
  httpAgentOptions: {
    keepAlive: true,
  },
};

// Security configuration
if (process.env.NODE_ENV === 'production') {
  // Content Security Policy
  const ContentSecurityPolicy = `
    default-src 'self';
    script-src 'self' 'unsafe-eval' 'unsafe-inline' https://unpkg.com;
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self' data:;
    connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL};
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
  `;

  nextConfig.headers = nextConfig.headers || [];
  nextConfig.headers().then(headers => {
    headers.push({
      source: '/(.*)',
      headers: [
        {
          key: 'Content-Security-Policy',
          value: ContentSecurityPolicy.replace(/\s{2,}/g, ' ').trim(),
        },
      ],
    });
  });
}

module.exports = nextConfig;