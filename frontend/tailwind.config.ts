import type { Config } from 'tailwindcss'
import { fontFamily } from 'tailwindcss/defaultTheme'

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		colors: {
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			osint: {
  				primary: '#0A84FF',
  				'primary-dark': '#0066CC',
  				'primary-light': '#4DA3FF',
  				secondary: '#4ADE80',
  				'secondary-dark': '#22C55E',
  				'secondary-light': '#86EFAC',
  				success: '#10B981',
  				warning: '#F59E0B',
  				error: '#EF4444',
  				info: '#3B82F6'
  			},
  			dark: {
  				bg: '#0F172A',
  				'bg-secondary': '#1E293B',
  				'bg-tertiary': '#334155',
  				surface: '#1E293B',
  				'surface-hover': '#334155',
  				border: '#334155',
  				text: '#F8FAFC',
  				'text-secondary': '#CBD5E1',
  				'text-muted': '#94A3B8'
  			},
  			light: {
  				bg: '#FFFFFF',
  				'bg-secondary': '#F8FAFC',
  				'bg-tertiary': '#F1F5F9',
  				surface: '#FFFFFF',
  				'surface-hover': '#F8FAFC',
  				border: '#E2E8F0',
  				text: '#0F172A',
  				'text-secondary': '#475569',
  				'text-muted': '#64748B'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			'fade-in': {
  				from: {
  					opacity: '0'
  				},
  				to: {
  					opacity: '1'
  				}
  			},
  			'fade-out': {
  				from: {
  					opacity: '1'
  				},
  				to: {
  					opacity: '0'
  				}
  			},
  			'slide-in-from-top': {
  				from: {
  					transform: 'translateY(-100%)'
  				},
  				to: {
  					transform: 'translateY(0)'
  				}
  			},
  			'slide-in-from-bottom': {
  				from: {
  					transform: 'translateY(100%)'
  				},
  				to: {
  					transform: 'translateY(0)'
  				}
  			},
  			'slide-in-from-left': {
  				from: {
  					transform: 'translateX(-100%)'
  				},
  				to: {
  					transform: 'translateX(0)'
  				}
  			},
  			'slide-in-from-right': {
  				from: {
  					transform: 'translateX(100%)'
  				},
  				to: {
  					transform: 'translateX(0)'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			'fade-in': 'fade-in 0.2s ease-out',
  			'fade-out': 'fade-out 0.2s ease-out',
  			'slide-in-from-top': 'slide-in-from-top 0.2s ease-out',
  			'slide-in-from-bottom': 'slide-in-from-bottom 0.2s ease-out',
  			'slide-in-from-left': 'slide-in-from-left 0.2s ease-out',
  			'slide-in-from-right': 'slide-in-from-right 0.2s ease-out'
  		},
  		fontFamily: {
  			sans: [
  				'var(--font-sans)',
                    ...fontFamily.sans
                ],
  			heading: [
  				'var(--font-heading)',
                    ...fontFamily.sans
                ],
  			mono: [
  				'var(--font-mono)',
                    ...fontFamily.mono
                ]
  		}
  	}
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
