import { Avatar, Box, Typography } from "@mui/material";
import StatRow from "../statHolders/StatRow";

interface Props {
    name: string,
    nickname?: string | null,
    w?: number | null,
    l?: number | null,
    d?: number | null,
    stance?: string | null,
    age: number,
    height: number | null,
    weight: number | null,
    reach: number | null,
}

export default function Sidebar({name, nickname, w, l, d, stance, age, height, weight, reach}: Props) {
    return (
        <Box p={2} sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-evenly",
        alignItems: "center",
        border: 1,
        }}>
            {/* Profile Section */}
            <Box sx={{
            display: "flex",
             flexDirection: "column",
             alignItems: "center"
             }}>
                <Avatar>AP</Avatar>
                <Typography variant="h6" textAlign={"center"}>{name}</Typography>
                <Typography variant="subtitle2">{nickname}</Typography>
                <Typography variant="subtitle1">{w}-{l}-{d}</Typography>
            </Box>
            {/* Stats Section */}
            <Box sx={{
            display: "flex",
             flexDirection: "column",
             alignItems: "center"
             }}>
                <StatRow title="Height" stat={height} />
                <StatRow title="Weight" stat={weight} />
                <StatRow title="Reach" stat={reach} />
            </Box>
            {/* Fantasy Score Section */}
            <Box sx={{
            display: "flex",
             flexDirection: "column",
             alignItems: "center"
             }}>
                <Typography noWrap variant="body1">Fantasy Score</Typography>
             </Box>
        </Box>
    )
}