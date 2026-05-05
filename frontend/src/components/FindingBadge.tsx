import React from 'react';

const severityConfig = {
    high: {
        bg: 'bg-red-100',
        text: 'text-red-700',
        border: 'border-red-200',
    },
    medium: {
        bg: 'bg-yellow-100',
        text: 'text-yellow-700',
        border: 'border-yellow-200',
    },
    low: {
        bg: 'bg-green-100',
        text: 'text-green-700',
        border: 'border-green-200',
    },
    info: {
        bg: 'bg-blue-100',
        text: 'text-blue-700',
        border: 'border-blue-200',
    },
};

type SeverityLevel = keyof typeof severityConfig;

interface FindingBadgeProps {
    text: string;
    severity?: SeverityLevel;
    className?: string;
}

export default function FindingBadge({ text, severity = 'info', className = '' }: FindingBadgeProps) {
    const { bg, text: textColor, border } = severityConfig[severity];

    return (
        <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bg} ${textColor} border ${border} ${className}`}
        >
            {text}
        </span>
    );
}