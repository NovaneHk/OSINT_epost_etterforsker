'use client';

import { useState, useEffect } from 'react';

const CONSENT_KEY = 'gdpr_consent';

export function GdprBanner() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const consent = window.localStorage.getItem(CONSENT_KEY);
            if (!consent) {
                setVisible(true);
            }
        }
    }, []);

    const handleAccept = () => {
        window.localStorage.setItem(CONSENT_KEY, 'true');
        setVisible(false);
    };

    const handleDecline = () => {
        // Allow use without consent (non-GDPR-required features still work)
        window.localStorage.setItem(CONSENT_KEY, 'false');
        setVisible(false);
    };

    if (!visible) return null;

    return (
        <div
            role="dialog"
            aria-modal="false"
            aria-label="Personvern og informasjonskapsler"
            className="fixed bottom-0 left-0 right-0 z-50 bg-gray-900 text-white px-4 py-4 shadow-lg"
        >
            <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <div className="flex-1 text-sm">
                    <p className="font-semibold mb-1">Personvern og databehandling</p>
                    <p className="text-gray-300 text-xs leading-relaxed">
                        Denne applikasjonen behandler personopplysninger som en del av B2B OSINT-undersøkelser.
                        Ved å akseptere samtykker du til behandling av data i henhold til GDPR og vår{' '}
                        <a href="/privacy" className="underline hover:text-white">
                            personvernerklæring
                        </a>
                        .
                    </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                        onClick={handleDecline}
                        className="px-4 py-2 text-sm border border-gray-500 rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-white"
                    >
                        Avvis
                    </button>
                    <button
                        onClick={handleAccept}
                        className="px-4 py-2 text-sm bg-indigo-600 rounded hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-white font-medium"
                    >
                        Aksepter
                    </button>
                </div>
            </div>
        </div>
    );
}
