import { Box, Typography } from "@mui/material"

interface Props {
    title: string,
    stat: number
} 

export default function QuickStatCard({title, stat}: Props) {
    return (
        <Box p={2} sx={{display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 1,
            border: 1,
        }}>
            <Typography variant="subtitle2">{title}</Typography>
            <Typography variant="h6">{stat}</Typography>
        </Box> 
    )
  
}