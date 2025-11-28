import { Box, Typography } from "@mui/material"

interface Props {
    title: string,
    stat: string | number
}
export default function StatRow({title, stat}: Props) {
    return (
        <Box sx={{display: "flex", justifyContent: "space-between"}}>
            <Typography variant="body2" sx={{color: "grey"}}>{title}</Typography>
            <Typography variant="body2">{stat}</Typography>
        </Box>
    )
}