export function formatScore(score: number | null): string {
    if (score === null) {
        return 'N/A';
    }

    // Convert score to percentage and round to nearest whole number
    const percentage = Math.round(score * 100);
    return `${percentage}%`;
}

export function getScoreColor(score: number | null): {
    text: string;
    bg: string;
    border: string;
} {
    if (score === null) {
        return {
            text: 'text-gray-600',
            bg: 'bg-gray-100',
            border: 'border-gray-200',
        };
    }

    if (score >= 0.8) {
        return {
            text: 'text-green-700',
            bg: 'bg-green-100',
            border: 'border-green-200',
        };
    }

    if (score >= 0.6) {
        return {
            text: 'text-yellow-700',
            bg: 'bg-yellow-100',
            border: 'border-yellow-200',
        };
    }

    if (score >= 0.4) {
        return {
            text: 'text-orange-700',
            bg: 'bg-orange-100',
            border: 'border-orange-200',
        };
    }

    return {
        text: 'text-red-700',
        bg: 'bg-red-100',
        border: 'border-red-200',
    };
}