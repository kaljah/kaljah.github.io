/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                accent: {
                    DEFAULT: '#ff6600',
                    hover: '#e65c00',
                    light: '#ff8533',
                },
                glass: {
                    DEFAULT: 'rgba(255, 255, 255, 0.7)',
                    dark: 'rgba(255, 255, 255, 0.15)',
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out forwards',
                'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                'slide-in-right': 'slideInRight 0.5s ease-out forwards',
                'pulse-glow': 'pulseGlow 2s infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(20px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                pulseGlow: {
                    '0%, 100%': { opacity: '1', boxShadow: '0 0 0 0 rgba(255, 102, 0, 0.4)' },
                    '50%': { opacity: '0.8', boxShadow: '0 0 0 10px rgba(255, 102, 0, 0)' },
                }
            },
            boxShadow: {
                'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
                'glass-hover': '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
            }
        },
    },
    plugins: [],
}
