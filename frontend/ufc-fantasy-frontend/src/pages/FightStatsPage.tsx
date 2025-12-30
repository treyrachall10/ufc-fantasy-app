import { Container, Grid, Box, Avatar, Typography } from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import DivergingProgressBar from "../components/statHolders/DivergingProgressBar";
import HeadToHeadStatCard from "../components/statHolders/HeadToHeadStatCard";
import FantasyScoreBreakdown from "../components/statHolders/FantasyScoreBreakdown";
import { RadarChart, Radar, PolarAngleAxis, PolarRadiusAxis, Legend, PolarGrid } from 'recharts';
import { HeadToHeadStats } from "../types/types";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

export default function FightStatsPage() { 
    const params = useParams()
    const id = params.id

    {/* API fetching*/}    
    const { data, isPending, error } = useQuery<HeadToHeadStats>({
        queryKey: ["HeadToHeadData", id],
        queryFn: () =>
            fetch(`http://localhost:8000/fight/${id}`)
                .then(r => r.json()),
    })

    if (isPending) return <span>Loading...</span>
    if (error || !data) return <span>Oops!</span>

    const fighterOne = data.fighterA
    const fighterTwo = data.fighterB

    return (
        <Container maxWidth='xl' sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
            {/* Bout Information */}
            <Box sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
            }}>
                <Typography>{data.bout}</Typography>
                <Typography>{data.event.event}</Typography>
            </Box>

            <Grid container spacing={2}>
                {/* Fighter 1 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterOne.full_name}
                        nickname={fighterOne.nick_name}
                        age={30}
                        height={fighterOne.height}
                        weight={fighterOne.weight}
                        reach={fighterOne.reach}
                        stance={fighterOne.stance}
                        record={fighterOne.record}
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
                            }}>
                                VS
                            </Avatar>
                        </Box>

                        {/* MAAAAAAAAAP TOOOOOO A FUNNNNNCCCTIIIIOOOOOON*/}
                        <HeadToHeadStatCard
                            title={"Total Strikes Landed"}
                            leftValue={data.fighterAFightStats.striking.total.landed}
                            rightValue={data.fighterBFightStats.striking.total.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Significant Strikes Landed"}
                            leftValue={data.fighterAFightStats.striking.significant.landed}
                            rightValue={data.fighterBFightStats.striking.significant.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Head Strikes Landed"}
                            leftValue={data.fighterAFightStats.striking.head.landed}
                            rightValue={data.fighterBFightStats.striking.head.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Body Strikes Landed"}
                            leftValue={data.fighterAFightStats.striking.body.landed}
                            rightValue={data.fighterBFightStats.striking.body.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Leg Strikes Landed"}
                            leftValue={data.fighterAFightStats.striking.leg.landed}
                            rightValue={data.fighterBFightStats.striking.leg.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Takedowns"}
                            leftValue={data.fighterAFightStats.grappling.takedowns.landed}
                            rightValue={data.fighterBFightStats.grappling.takedowns.landed}
                        />
                        <HeadToHeadStatCard
                            title={"Ctrl. Time"}
                            leftValue={data.fighterAFightStats.grappling.ctrl_time}
                            rightValue={data.fighterBFightStats.grappling.ctrl_time}
                        />
                        <HeadToHeadStatCard
                            title={"Sub Attempts"}
                            leftValue={data.fighterAFightStats.grappling.sub_att}
                            rightValue={data.fighterBFightStats.grappling.sub_att}
                        />
                    </Box>
                </Grid>

                {/* Fighter 2 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterTwo.full_name}
                        nickname={fighterTwo.nick_name}
                        age={30}
                        height={fighterTwo.height}
                        weight={fighterTwo.weight}
                        reach={fighterTwo.reach}
                        stance={fighterTwo.stance}
                        record={fighterTwo.record}
                    />
                </Grid>
            </Grid>

            <FantasyScoreBreakdown 
                names={[data.fighterA.full_name, data.fighterB.full_name]}
                fantasyScores={[data.fighterAFantasy, data.fighterBFantasy]}
                />


        </Container>
    )
}
