import { Box, LinearProgress, Typography } from "@mui/material";
import FantasyStatRow from "./FantasyStatRow";
import StatToggler from "../Controls/StatToggler";
import { useState } from "react";
import { RadarChart, Radar, PolarAngleAxis, PolarRadiusAxis, Legend, PolarGrid } from 'recharts';
import { DetailedFantasyScore } from "../../types/types";

interface FantasyScoreBreakdownProps {
    names: string[],
    fantasyScores: DetailedFantasyScore[]
}

export default function FantasyScoreBreakdown({names, fantasyScores}: FantasyScoreBreakdownProps) {
    
    const fighterOneRows = [
        { icon: <Box/>, title: "Win", points: fantasyScores[0].fight.points_win, value: (fantasyScores[0].fight.points_win/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Significant Strikes", points: fantasyScores[0].breakdown.points_sig_str_landed, value: (fantasyScores[0].breakdown.points_sig_str_landed/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Knockdown", points: fantasyScores[0].breakdown.points_knockdowns, value: (fantasyScores[0].breakdown.points_knockdowns/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Takedowns Landed", points: fantasyScores[0].breakdown.points_td_landed, value: (fantasyScores[0].breakdown.points_td_landed/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Submission Attempts", points: fantasyScores[0].breakdown.points_sub_att, value: (fantasyScores[0].breakdown.points_sub_att/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Reversals", points: fantasyScores[0].breakdown.points_reversals, value: (fantasyScores[0].breakdown.points_reversals/fantasyScores[0].total) * 100 },
        { icon: <Box/>, title: "Control Time", points: fantasyScores[0].breakdown.points_ctrl_time, value: (fantasyScores[0].breakdown.points_ctrl_time/fantasyScores[0].total) * 100 }
    ]

    const fighterTwoRows= [
        { icon: <Box/>, title: "Win", points: fantasyScores[1].fight.points_win, value: (fantasyScores[1].fight.points_win/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Significant Strikes", points: fantasyScores[1].breakdown.points_sig_str_landed, value: (fantasyScores[1].breakdown.points_sig_str_landed/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Knockdowns", points: fantasyScores[1].breakdown.points_knockdowns, value: (fantasyScores[1].breakdown.points_knockdowns/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Takedowns Landed", points: fantasyScores[1].breakdown.points_td_landed, value: (fantasyScores[1].breakdown.points_td_landed/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Submission Attempts", points: fantasyScores[1].breakdown.points_sub_att, value: (fantasyScores[1].breakdown.points_sub_att/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Reversals", points: fantasyScores[1].breakdown.points_reversals, value: (fantasyScores[1].breakdown.points_reversals/fantasyScores[1].total) * 100 },
        { icon: <Box/>, title: "Control Time", points: fantasyScores[1].breakdown.points_ctrl_time, value: (fantasyScores[1].breakdown.points_ctrl_time/fantasyScores[1].total) * 100 }
    ]


    function handleFantasyToggle(event: React.MouseEvent<HTMLElement>, value: string){
        if (!value) return;
        
        setSelectedFighter(value);
        if (value === "Fighter A") {
            setFantasyRows(fighterOneRows);
            setFantasyTotal(fantasyScores[0].total)
        } else {
            setFantasyRows(fighterTwoRows);
            setFantasyTotal(fantasyScores[1].total)
        }
    }

    const [fantasyRows, setFantasyRows] = useState(fighterOneRows);
    const [fantasyTotal, setFantasyTotal] = useState(fantasyScores[0].total)
    const [selectedFighter, setSelectedFighter] = useState("Fighter A");

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
                    buttonText={[names[0], names[1]]}
                    buttonValue={["Fighter A", "Fighter B"]}
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
                <Typography>{fantasyTotal}</Typography>
                <Typography>Points</Typography>
            </Box>
            <Box sx={{
                    display: "flex",
                    flexDirection: "column",
                    width: "100%",
                    gap: 1
                    }}>
                {/* Fantasy Progress Bars*/}
                    {fantasyRows.map((row, index) =>
                    <FantasyStatRow
                            key={index}
                            icon={row.icon}
                            title={row.title}
                            points={row.points}
                            value={row.value}
                            />
                    )}
            </Box>
        </Box>
    )
}