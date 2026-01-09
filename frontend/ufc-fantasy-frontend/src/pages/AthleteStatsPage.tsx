import { Container, Grid, Box, Typography } from "@mui/material";
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

    return (
        <Container maxWidth="xl">
            <Grid container spacing={2}>

                {/* Sidebar */}
                <Grid size={{ xs: 12, md: 2}}>
                    <Sidebar 
                        name={fighterData.fighter.full_name}
                        nickname={fighterData.fighter.nick_name}
                        age={30}
                        height={fighterData.fighter.height}
                        weight={fighterData.fighter.weight}
                        reach={fighterData.fighter.reach}
                        stance={fighterData.fighter.stance}
                        record={fighterData.fighter.record}
                    />
                </Grid>
                {/* Body */}
                <Grid size={{ xs: 12, md: 10 }}>
                    <Box sx={{display: "flex",
                    flexDirection: "column",
                    gap: 1
                    }}>
                        {/* QuickStats */}
                        <Typography variant="subtitle2">Career Stats:</Typography>
                        <Grid container spacing={2} sx={{
                            display: "flex",
                            justifyContent: "space-between",
                        }}>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="SLPM" stat={slpm.toFixed(2)}/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR DEF" stat={strDef.toFixed(2)} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR ACC" stat={strAcc.toFixed(2)} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD%" stat={tdDef.toFixed(2)} />
                            </Grid>
                            
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD ACC" stat={tdAcc.toFixed(2)} />
                            </Grid>
                            
                        </Grid>
                        {/* Fantsy Chart and W/L Chart */}
                        <Grid container spacing={2}>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <Typography variant="subtitle2">Fantasy Trend Chart (last 3 fights): </Typography>
                                <FantasyTrendLineChart data={fantasyTrendData}/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <Typography variant="subtitle2">Method of Victory/Loss: </Typography>
                                <WinLossChart
                                record={fighterData.fighter.record}
                                />
                            </Grid>
                        </Grid>
                        {/* FightList and Interesting Stats */}
                        <Grid container spacing={2}>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <FightsList/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <QuickStatCard title="Control %" stat={'32'} />
                            </Grid>
                        </Grid>
                    </Box>
                </Grid>
            </Grid>
        </Container>
        
    )
}