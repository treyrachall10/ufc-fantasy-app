import { Box, Typography, LinearProgress } from "@mui/material"

interface FantasyStatRowProps {
    title: string,
    icon: React.ReactNode,
    points: number,
    value: number
}
export default function FantasyStatRow({
    icon,
    title,
    points,
    value,
    }: FantasyStatRowProps) {
  return (
    <Box sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        }}>
        {/* Fantasy Progress Bars */}
        <Box sx={{
            display: "flex",
            justifyContent: "space-between",
            width: "100%",
        }}>
            <Box sx={{ display: "flex", gap: 1 }}>
            <Typography>{icon}</Typography>
            <Typography>{title}</Typography>
            </Box>
            <Typography>+ {points}</Typography>
        </Box>

        <LinearProgress variant="determinate" value={value} />
    </Box>
  );
}
