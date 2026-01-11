import { Container, Grid, Box, Typography, Stack} from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import QuickStatCard from "../components/statHolders/QuickStatCard";
import FightsList from "../components/lists/FightsList";
import WinLossChart from "../components/charts/WinLossChart";
import FantasyTrendLineChart from "../components/charts/FantasyTrendLineChart";
import { FantasyFightScore, FighterWithCareerStats } from "../types/types";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";

export default function AthleteStatsPage(){
    const  params = useParams()
    const id = params.id; 
    {/* API fetching*/}    
    {/*
    const { data: fighterData,
            isPending: fighterPending,
            error: fighterError } = useQuery<FighterWithCareerStats>({
            queryKey: ['fighterStatsData', id],
            queryFn: () => fetch(`http://localhost:8000/fighter/${id}`).then(r => r.json()),
        })

    const { data: fantasyScoresData,
            isPending: fantasyPending,
            error: fantasyError } = useQuery<FantasyFightScore[]>({
            queryKey: ['fighterFantasyTrend', id],
            queryFn: () => fetch(`http://localhost:8000/fights/${id}/fantasy-scores/recent`).then(r => r.json()),
        })
    
    if (fighterPending || fantasyPending) return <span>Loading...</span>
    if (fighterError || fantasyError) return <span>Oops!</span>

    // Strikes landed per minute (fight time is in seconds)
    const slpm =
    fighterData.total_fight_time > 0
        ? fighterData.striking.total.landed / (fighterData.total_fight_time / 60)
        : 0;

    // Striking accuracy
    const strAcc =
    fighterData.striking.significant.attempted > 0
        ? (fighterData.striking.significant.landed / fighterData.striking.significant.attempted) * 100
        : 0;

    // Striking defense
    const strDef =
    fighterData.opponent.striking.significant.attempted > 0
        ? (1 - fighterData.opponent.striking.significant.landed / fighterData.opponent.striking.significant.attempted) * 100
        : 100;

    // Takedown accuracy
    const tdAcc =
    fighterData.grappling.takedowns.attempted > 0
        ? (fighterData.grappling.takedowns.landed / fighterData.grappling.takedowns.attempted) * 100
        : 0;

    // Takedown defense
    const tdDef =
    fighterData.opponent.grappling.takedowns.attempted > 0
        ? (1 - fighterData.opponent.grappling.takedowns.landed / fighterData.opponent.grappling.takedowns.attempted) * 100
        : 100;

    // Fantasy Trend Points
    const fantasyTrendData = fantasyScoresData.map(fantasyData => ({
        bout: fantasyData.bout,
        points: fantasyData.fight_total_points,
        date: fantasyData.date
    }))
        */}

        const mockData = {
        wins: {
            total: 12,
            ko_tko_wins: 12,
            tko_doctor_stoppage_wins: 1,
            submission_wins: 8,
            unanimous_decision_wins: 10,
            split_decision_wins: 4,
            majority_decision_wins: 2,
            dq_wins: 0,
        },
        losses: {
            total: 3,
            ko_tko_losses: 1,
            tko_doctor_stoppage_losses: 1,
            submission_losses: 2,
            unanimous_decision_losses: 4,
            split_decision_losses: 1,
            majority_decision_losses: 0,
            dq_losses: 0,
        },
        draws: 1,
        };



    return (
        <Container maxWidth="laptop">
                <Stack direction={'column'} spacing={2}>
                    {/*Header*/}
                        <Stack sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: {mobile: 'center', laptop: 'flex-start'},
                                alignItems: {mobile: 'center', laptop: 'flex-start'},
                        }}>
                            <Typography variant="h2">Alex Pereira</Typography>
                            <Typography variant="body" color="text.secondary">"Poatan"</Typography>
                            <Typography variant="h3">10-2-0</Typography>
                        </Stack>
                            <Grid container spacing={3} justifyContent={{ mobile: 'center', laptop: 'flex-start' }}>
                                {/*Meta Data Box*/}
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                        <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                            <Typography variant="metaLabel" color="text.secondary">Height: </Typography>
                                            <Typography variant="metaText">60"</Typography>
                                        </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Weight: </Typography>
                                        <Typography variant="metaText">205lbs</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Reach: </Typography>
                                        <Typography variant="metaText">60"</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Stance: </Typography>
                                        <Typography variant="metaText">Orthodox</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Dob: </Typography>
                                        <Typography variant="metaText">12-02-2003</Typography>
                                    </Stack>
                                </Grid>
                            </Grid>
                            {/*Body Contents*/}
                            <Grid container spacing={1}>
                                {/*KPI Contents*/}
                                <Grid container size={12} spacing={1} sx={{ bgcolor: 'dashboardBlack.main', borderRadius: 2, p: 1}}>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">8.85</Typography>
                                            <Typography variant="caption">SLPM</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">58.95</Typography>
                                            <Typography variant="caption">Str. Def.</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">56.89</Typography>
                                            <Typography variant="caption">Str. Acc.</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">70%</Typography>
                                            <Typography variant="caption">Td%</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">34.44</Typography>
                                            <Typography variant="caption">Td Acc.</Typography>
                                        </Stack>
                                    </Grid>                                                                        
                                </Grid>
                                {/*Fantasy Trend Chart*/}
                                <Grid size={12}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2, overflow: "hidden" }}>
                                        <FantasyTrendLineChart data={[
                                            {bout: 'pereira vs. blachowiz', points: 120, date: '12/12/12'},
                                            {bout: 'pereira vs. ankalaev', points: 80, date: '12/12/12'},
                                            {bout: 'pereira vs. ankalaev', points: 30, date: '12/12/12'},
                                            {bout: 'pereira vs. ankalaev', points: 40, date: '12/12/12'},
                                            {bout: 'pereira vs. adesanya', points: 100, date: '12/12/12'}
                                        ]}/>
                                    </Box>
                                </Grid>
                                {/*Win Loss Chart*/}
                                <Grid size={{mobile: 12, laptop: 7}}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2, overflow: 'hidden'}}>
                                        <WinLossChart record={mockData}/>
                                    </Box>
                                </Grid>
                                {/*Past Fights List*/}
                                <Grid size={{mobile: 12, laptop: 5}}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2 }} />
                                </Grid>
                            </Grid>
                </Stack>
        </Container>
        
    )
}