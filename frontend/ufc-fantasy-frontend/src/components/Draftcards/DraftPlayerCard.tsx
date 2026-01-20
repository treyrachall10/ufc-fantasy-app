import React from 'react';
import { Box, Avatar, Typography } from '@mui/material';

interface DraftPlayerCardProps {
    name: string;
    subtitle: React.ReactNode;
    weightClass: string;
    /** 
     - 'roster': Used in the "Current Roster" column.
     - 'history': Used in the "Past Picks" column 
     -  default 'roster'
     */
    variant?: 'roster' | 'history';
}

/**
 * Workflow:
 * 1. Receives fighter data and context via props.
 * 2. Determines styling flags (`isRoster`, `isHistory`) based on `variant`.
 * 3. Applies unified layout styles (Box/Flex) with conditional adjustments for:
 *    - Font weights (History is often bolder/more distinct).
 *    - Spacing/Gap.
 *    - Border rendering (Controlled by theme variables).
 */
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
        justifyContent: 'space-between', // weight class stays on the far right
        mb: 0,
        border: '1px solid',
        borderColor: 'whiteAlpha20.main',
    };

    // Define text styling variants
    const subtitleColor = 'text.secondary';
    const rightSideColor = 'white';

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
