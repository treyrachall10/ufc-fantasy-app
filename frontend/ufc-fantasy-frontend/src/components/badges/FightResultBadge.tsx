import { Box, Stack, Typography } from "@mui/material";

interface FightResultBadge {
    result: string;
    method: string;
}

export default function FightResultBadge({result, method}: FightResultBadge){


    const bgColor = result === 'W'? 'brandAlpha75.main': 'brand.light'

    return (
        <Box sx={{
            display: "inline-flex",
            justifyContent: "flex-start",
            alignItems: "center",
            gap: .25
        }}>
            {/* Result */}
            <Box sx={{
                borderRadius: 1,
                backgroundColor: bgColor,
                border: 'solid .5px',
                borderColor: 'brand.main',
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: 42,
                width: 42,
            }}>
                <Typography sx={{
                                fontWeight: '500', 
                                textAlign: 'center', 
                                lineHeight: '100%'}}
                                >{result.toUpperCase()}
                </Typography>
            </Box>
            {/* Method */}
            <Box sx={{
                width: 24,
                height: 42,
                backgroundColor: 'brand.light',
                borderRadius: 1,
                border: 'solid .5px',
                borderColor: 'brand.main',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}>
                <Typography sx={{
                    fontWeight: 500,
                    writingMode: 'vertical-lr',
                    transform: 'rotate(180deg)',
                    transformOrigin: 'center',
                    lineHeight: '100%'
                    }}>
                        {method.toUpperCase()}
                    </Typography>
            </Box>
        </Box>
    )
}