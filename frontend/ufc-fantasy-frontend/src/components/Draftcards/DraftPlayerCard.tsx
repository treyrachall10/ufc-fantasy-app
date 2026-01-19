import React from 'react';
import { Box, Avatar, Typography } from '@mui/material';

interface DraftPlayerCardProps {
    name: string;
    subtitle: React.ReactNode;
    weightClass: string;
    variant?: 'roster' | 'history';
}

export default function DraftPlayerCard({
    name,
    subtitle,
    weightClass,
    variant = 'roster'
}: DraftPlayerCardProps) {

    // --- Styles based on variant ---
    const isRoster = variant === 'roster';
    const isHistory = variant === 'history';

    // Container Styles
    const containerSx = {
        p: 1.5,
        borderRadius: 2,
        backgroundColor: 'whiteAlpha20.main',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between', // Unified Layout: Always push apart
        mb: 0,
        border: '1px solid',
        borderColor: 'whiteAlpha20.main',
    };

    // Text Colors
    const subtitleColor = 'text.secondary'; // Default for both as requested
    const rightSideColor = 'white'; // Always white as requested

    return (
        <Box sx={containerSx}>

            {/* LEFT SIDE GROUP (Avatar + Info) */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: isHistory ? 2 : 1.5 }}>
                <Avatar sx={{ width: 32, height: 32, bgcolor: 'brand.main' }}></Avatar>
                <Box>
                    <Typography variant="bodySmall" sx={{
                        fontWeight: isHistory ? 700 : 600,
                        lineHeight: 1.2,
                        display: 'block',
                        color: 'white'
                    }}>
                        {name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: subtitleColor, display: 'block', fontSize: isHistory ? '0.75rem' : undefined }}>
                        {subtitle}
                    </Typography>
                </Box>
            </Box>

            {/* RIGHT SIDE CONTENT (Weight Class) */}
            <Typography variant="bodySmall" sx={{ color: rightSideColor, fontWeight: 600 }}>
                {weightClass}
            </Typography>
        </Box>
    );
}
