import { Container, Grid, Box, Avatar, Typography} from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import DivergingProgressBar from "../components/statHolders/DivergingProgressBar";
import HeadToHeadStatCard from "../components/statHolders/HeadToHeadStatCard";
import FantasyScoreBreakdown from "../components/statHolders/FantasyScoreBreakdown";
import { RadarChart, Radar, PolarAngleAxis, PolarRadiusAxis, Legend, PolarGrid } from 'recharts';

interface FightStatsPageProps {
    fightId: number;
}

export default function FightStatsPage({fightId}: FightStatsPageProps) {
    const fighterOne = {
        name: "Alex Pereira",
        nickname: "Poatan",
        age: 36,
        height: 193, // cm
        weight: 93, // kg
        reach: 203, // cm
        stance: "Orthodox",
        w: 10,
        l: 2,
        d: 0
    };

    const fighterTwo = {
        name: "Jamal Hill",
        nickname: "Sweet Dreams",
        age: 32,
        height: 193, // cm
        weight: 93, // kg
        reach: 201, // cm
        stance: "Southpaw",
        w: 12,
        l: 2,
        d: 0
    };

        const data = [
        {
            subject: 'Sig. Str',
            A: 30,
            B: 65,
            fullmark: 150
        },
                {
            subject: 'Takedowns',
            A: 3,
            B: 0,
            fullmark: 150
        },
                {
            subject: 'Knockdowns',
            A: 0,
            B: 2,
            fullmark: 150
        },
                {
            subject: 'Sub Att',
            A: 2,
            B: 0,
            fullmark: 150
        },
                {
            subject: 'Ctrl Time',
            A: 30,
            B: 65,
            fullmark: 150
        },
]
    return (
        <Container maxWidth='xl' sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
            {/* Bout Information */}
            <Box sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
            }}>
                <Typography>UFC 300: LIGHT HEAVYWEIGHT CHAMPIONSHIP</Typography>
                <Typography>T-Mobile Arena, Las Vegas - April 2024</Typography>
            </Box>
            <Grid container spacing={2}>
                {/* Fighter 1 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterOne.name}
                        nickname={fighterOne.nickname}
                        age={fighterOne.age}
                        height={fighterOne.height}
                        weight={fighterOne.weight}
                        reach={fighterOne.reach}
                        stance={fighterOne.stance}
                        w={fighterOne.w}
                        l={fighterOne.l}
                        d={fighterOne.d}
                    />
                </Grid>
                {/* Middle Section*/}
                <Grid size={{xs: 4, md: 8}} spacing={2}>
                    <Box sx={{
                        display:'flex',
                        flexDirection: 'column',
                        justifyContent: "center",
                        width: '100%',
                        gap: 1
                        }}>
                            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                                <Avatar sx={{
                                    width: { xs: 48, sm: 56, md: 64, lg: 72 },
                                    height: { xs: 48, sm: 56, md: 64, lg: 72 },
                                    fontSize: { xs: 18, sm: 20, md: 22, lg: 24 },
                                }}>VS</Avatar>
                            </Box>
                        {/* MAAAAAAAAAP TOOOOOO A FUNNNNNCCCTIIIIOOOOOON*/}
                        <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                        <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                        <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                        <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                    </Box>
                </Grid>
                {/* Fighter 2 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterTwo.name}
                        nickname={fighterTwo.nickname}
                        age={fighterTwo.age}
                        height={fighterTwo.height}
                        weight={fighterTwo.weight}
                        reach={fighterTwo.reach}
                        stance={fighterTwo.stance}
                        w={fighterTwo.w}
                        l={fighterTwo.l}
                        d={fighterTwo.d}
                    />
                </Grid>
            </Grid>
            <FantasyScoreBreakdown/>
            {/* Radar Chart Section*/}
            <Box sx={{ display: 'flex', justifyContent: 'center', border: 1}}>
                <RadarChart style={{width: '100%', height: '500px', aspectRatio: 1}} responsive data={data}>
                    <PolarGrid/>
                    <PolarRadiusAxis angle={30} domain={[0, 100]} />
                        <Radar
                            name="Mike"
                            dataKey="A"
                            stroke="#8884d8"
                            fill="#8884d8"
                            fillOpacity={0.6}
                            isAnimationActive={true}
                            />
                            <Radar
                            name="Lily"
                            dataKey="B"
                            stroke="#82ca9d"
                            fill="#82ca9d"
                            fillOpacity={0.6}
                            isAnimationActive={true}
                            />
                            <Legend />
                </RadarChart>
            </Box>
        </Container>
    )
}