import { LinearProgress, Box, Typography } from '@mui/material';
import { SxProps, Theme } from "@mui/material/styles";

interface DivergingProgressBarProps {
  leftValue: number;
  rightValue: number;
  leftColor?: string;
  rightColor?: string;
  sx?: SxProps<Theme>;
}

export default function DivergingProgressBar({
    leftValue,
    rightValue,
    leftColor = 'red',
    rightColor = 'black',
    sx
    }: DivergingProgressBarProps){

    const total = leftValue + rightValue;
    const leftPercent = total > 0 ? (leftValue / total) * 100 : 50;
    const rightPercent = total > 0 ? (rightValue / total) * 100 : 50;
    return (
        <Box
            sx={{
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                pt: 1
            }}
        >
        <LinearProgress variant='determinate' value={leftPercent}
        sx={{
            backgroundColor: rightColor,

            "& .MuiLinearProgress-bar": {
                backgroundColor: leftColor
        },
        ...sx
        }}
    />
        <Typography variant='body2' sx={{
            color: leftValue > rightValue? {leftColor} : {rightColor}
        }}>{leftPercent > rightValue? leftPercent.toFixed(0): rightPercent.toFixed(0)}% Advantage</Typography>
        </Box>
    )
}