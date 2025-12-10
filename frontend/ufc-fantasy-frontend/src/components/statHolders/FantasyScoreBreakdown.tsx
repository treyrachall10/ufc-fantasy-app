import { Box, LinearProgress, Typography } from "@mui/material";
import FantasyStatRow from "./FantasyStatRow";
import StatToggler from "../Controls/StatToggler";
import { useState } from "react";
import { RadarChart, Radar, PolarAngleAxis, PolarRadiusAxis, Legend, PolarGrid } from 'recharts';


export default function FantasyScoreBreakdown() {
    
    const fighterOneStats = [
        { icon: <Box/>, title: "Win", points: +20, value: 70 },
        { icon: <Box/>, title: "Significant Strikes", points: +12, value: 45 },
        { icon: <Box/>, title: "Submission Attempts", points: +8, value: 30 },
        { icon: <Box/>, title: "Knockdowns", points: +10, value: 85 },
        { icon: <Box/>, title: "Control Time", points: +10, value: 85 }
    ]

    const fighterTwoStats = [
        { icon: <Box/>, title: "Win", points: +10, value: 60 },
        { icon: <Box/>, title: "Significant Strikes", points: +1, value: 15 },
        { icon: <Box/>, title: "Submission Attempts", points: +2, value: 30 },
        { icon: <Box/>, title: "Knockdowns", points: +30, value: 15 },
        { icon: <Box/>, title: "Control Time", points: +0, value: 85 }
    ]


    function handleFantasyToggle(event: React.MouseEvent<HTMLElement>, value: string){
        if (!value) return;
        
        setSelectedFighter(value);

        if (value === "Fighter 1") {
            setFantasyStats(fighterOneStats);
        } else {
            setFantasyStats(fighterTwoStats);
        }
    }

    const [fantasyStats, setFantasyStats] = useState(fighterOneStats);
    const [selectedFighter, setSelectedFighter] = useState("Fighter 1");

    return (
        <Box sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            border: 1,
            p: 1
            }}>
            {/* Title and Button Section*/}
            <Box sx={{
                display: "flex",
                justifyContent: "space-between",
                width: "100%"
            }}>
                <Typography>Fantasy Score Breakdown</Typography>
                <StatToggler 
                    handler={handleFantasyToggle}
                    selectedValue={selectedFighter}
                    buttonText={["Alex Pereira", "Jamal Hill"]}
                    buttonValue={["Fighter 1", "Fighter 2"]}
                    />
            </Box>
            {/* Fantasy Score Box*/}
            <Box sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                width: "15%",
                border: 1
            }}>
                <Typography>Total Fantasy Score</Typography>
                <Typography>287</Typography>
                <Typography>Points</Typography>
            </Box>
            <Box sx={{
                    display: "flex",
                    flexDirection: "column",
                    width: "100%",
                    gap: 1
                    }}>
                {/* Fantasy Progress Bars*/}
                    {fantasyStats.map((stat, index) =>
                    <FantasyStatRow
                            key={index}
                            icon={stat.icon}
                            title={stat.title}
                            points={stat.points}
                            value={stat.value}
                            />
                    )}
            </Box>
        </Box>
    )
}