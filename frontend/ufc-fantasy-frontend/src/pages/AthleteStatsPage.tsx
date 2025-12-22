import { Container, Grid, Box } from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import QuickStatCard from "../components/statHolders/QuickStatCard";
import FightsList from "../components/lists/FightsList";
import WinLossChart from "../components/charts/WinLossChart";
import FantasyTrendLineChart from "../components/charts/FantasyTrendLineChart";
import { FighterWithCareerStats } from "../types/types";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";

export default function AthleteStatsPage(){
    const  params = useParams()
    const id = params.id;
    {/* API fetching*/}    
    const { data, isPending, error } = useQuery<FighterWithCareerStats>({
            queryKey: ['fighterStatsData', id],
            queryFn: () => fetch(`http://localhost:8000/fighter/${id}`).then(r => r.json()),
        })
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>
    
    // Strikes landed per minute (fight time is in seconds)
    const slpm =
    data.total_fight_time > 0
        ? data.striking.total.landed / (data.total_fight_time / 60)
        : 0;

    // Striking accuracy
    const strAcc =
    data.striking.significant.attempted > 0
        ? (data.striking.significant.landed / data.striking.significant.attempted) * 100
        : 0;

    // Striking defense
    const strDef =
    data.opponent.striking.significant.attempted > 0
        ? (1 - data.opponent.striking.significant.landed / data.opponent.striking.significant.attempted) * 100
        : 100;

    // Takedown accuracy
    const tdAcc =
    data.grappling.takedowns.attempted > 0
        ? (data.grappling.takedowns.landed / data.grappling.takedowns.attempted) * 100
        : 0;

    // Takedown defense
    const tdDef =
    data.opponent.grappling.takedowns.attempted > 0
        ? (1 - data.opponent.grappling.takedowns.landed / data.opponent.grappling.takedowns.attempted) * 100
        : 100;

    return (
        <Container maxWidth="xl">
            <Grid container spacing={2}>

                {/* Sidebar */}
                <Grid size={{ xs: 12, md: 2}}>
                    <Sidebar 
                        name={data.fighter.full_name}
                        nickname={data.fighter.nick_name}
                        age={30}
                        height={data.fighter.height}
                        weight={data.fighter.weight}
                        reach={data.fighter.reach}
                        stance={data.fighter.stance}
                        record={data.fighter.record}
                    />
                </Grid>
                {/* Body */}
                <Grid size={{ xs: 12, md: 10 }}>
                    <Box sx={{display: "flex",
                    flexDirection: "column",
                    gap: 1
                    }}>
                        {/* QuickStats */}
                        <Grid container spacing={2} sx={{
                            display: "flex",
                            justifyContent: "space-between",
                        }}>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="SLPM" stat={slpm.toFixed(2)}/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD%" stat={tdDef.toFixed(2)} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR ACC" stat={strAcc.toFixed(2)} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD ACC" stat={tdAcc.toFixed(2)} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR DEF" stat={strDef.toFixed(2)} />
                            </Grid>
                        </Grid>
                        {/* Fantsy Chart and W/L Chart */}
                        <Grid container spacing={2}>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <FantasyTrendLineChart/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <WinLossChart
                                record={data.fighter.record}
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