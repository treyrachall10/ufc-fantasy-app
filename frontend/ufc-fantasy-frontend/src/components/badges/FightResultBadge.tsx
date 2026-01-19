import { Box, Stack, Typography } from "@mui/material";

interface FightResultBadge {
    result: string;
    method: string;
}

export default function FightResultBadge({result, method}: FightResultBadge){
    let displayResult = result;
    let displayMethod = method;
    let bgColor;

    // Determine bgcolor and result
    if (result === 'W') {
        bgColor = 'brandAlpha75.main';
    } else if (result === 'L') {
        bgColor = 'brand.light';
    } else if (result === 'D' && method == null) {
        displayResult = 'NC';
        displayMethod = 'NC'
        bgColor = 'transparent';
    } else if (result === 'D') {
        bgColor = 'transparent'
    } 

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
                                >{displayResult}
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
                        {displayMethod}
                    </Typography>
            </Box>
        </Box>
    )
}