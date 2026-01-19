import { Container, Grid, Box, Typography, Stack} from "@mui/material";
import { DataGrid } from '@mui/x-data-grid';
import Sidebar from "../components/layout/Sidebar";
import QuickStatCard from "../components/statHolders/QuickStatCard";
import FightsList from "../components/lists/FightsList";
import WinLossChart from "../components/charts/WinLossChart";
import FantasyTrendLineChart from "../components/charts/FantasyTrendLineChart";
import FightResultBadge from "../components/badges/FightResultBadge";
import { FantasyFightScore, Fight, FighterWithCareerStats, FightForFighter } from "../types/types";
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
    
    const { data: fighterFightsData,
        isPending: fightsPending,
        error: fightsError } = useQuery<FightForFighter[]>({
        queryKey: ['fighterFights', id],
        queryFn: () => fetch(`http://localhost:8000/fights/${id}`).then(r => r.json()),
    })

    if (fighterPending || fantasyPending || fightsPending) return <span>Loading...</span>
    if (fighterError || fantasyError || fightsError) return <span>Oops!</span>

    // Strikes landed per minute (fight time is in seconds)
    const slpm =
    (fighterData.total_fight_time > 0
        ? fighterData.striking.total.landed / (fighterData.total_fight_time / 60)
        : 0).toFixed(1);

    // Striking accuracy
    const strAcc =
    Number((fighterData.striking.significant.attempted > 0
        ? (fighterData.striking.significant.landed / fighterData.striking.significant.attempted) * 100
        : 0).toFixed(1));

    // Striking defense
    const strDef =
    Number((fighterData.opponent.striking.significant.attempted > 0
        ? (1 - fighterData.opponent.striking.significant.landed / fighterData.opponent.striking.significant.attempted) * 100
        : 100).toFixed(1));

    // Takedown accuracy
    const tdAcc =
    Number((fighterData.grappling.takedowns.attempted > 0
        ? (fighterData.grappling.takedowns.landed / fighterData.grappling.takedowns.attempted) * 100
        : 0).toFixed(1));

    // Takedown defense
    const tdDef =
    Number((fighterData.opponent.grappling.takedowns.attempted > 0
        ? (1 - fighterData.opponent.grappling.takedowns.landed / fighterData.opponent.grappling.takedowns.attempted) * 100
        : 100).toFixed(1));

    // Fantasy Trend Points
    const fantasyTrendData = fantasyScoresData.map(fantasyData => ({
        bout: fantasyData.bout,
        points: fantasyData.fight_total_points,
        date: fantasyData.date
    }))

    
    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns = [
        {field: 'result', headerName: 'Result', renderCell: (params: any) => {return <FightResultBadge result={params.row.result} method={params.row.method}/>}},
        {field: 'opponent', headerName: 'Opponent', flex: 1},
        {field: 'event', headerName: 'Event', flex: 1 }, //Flex keeps consistent sizing when chaning window size
        {field: 'round', headerName: 'Round', flex: 1 },
        {field: 'date', headerName: 'Date', flex: 1},
    ];
    
    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out events with long name
    const rows = fighterFightsData.map((data) => ({
            id: data.fight_id,
            result: data.result,
            method: data.method,
            opponent: data.opponent,
            event: data.event.event,
            round: data.round,
            date: data.event.date,
    }));

    // Dynamic data for method win data
    const winChartData = {
        wins: {
            total: fighterData.fighter.record.wins.total,
            ko_tko_wins: fighterData.fighter.record.wins.ko_tko_wins,
            tko_doctor_stoppage_wins: fighterData.fighter.record.wins.tko_doctor_stoppage_wins,
            submission_wins: fighterData.fighter.record.wins.submission_wins,
            unanimous_decision_wins: fighterData.fighter.record.wins.unanimous_decision_wins,
            split_decision_wins: fighterData.fighter.record.wins.split_decision_wins,
            majority_decision_wins: fighterData.fighter.record.wins.majority_decision_wins,
            dq_wins: fighterData.fighter.record.wins.dq_wins,
        },
        losses: {
            total: fighterData.fighter.record.losses.total,
            ko_tko_losses: fighterData.fighter.record.losses.ko_tko_losses,
            tko_doctor_stoppage_losses: fighterData.fighter.record.losses.tko_doctor_stoppage_losses,
            submission_losses: fighterData.fighter.record.losses.submission_losses,
            unanimous_decision_losses: fighterData.fighter.record.losses.unanimous_decision_losses,
            split_decision_losses: fighterData.fighter.record.losses.split_decision_losses,
            majority_decision_losses: fighterData.fighter.record.losses.majority_decision_losses,
            dq_losses: fighterData.fighter.record.losses.dq_losses,
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
                            <Typography variant="h2">{fighterData.fighter.full_name}</Typography>
                            <Typography variant="body" color="text.secondary">"{fighterData.fighter.nick_name}"</Typography>
                            <Typography variant="h3">{fighterData.fighter.record.wins.total}-{fighterData.fighter.record.losses.total}-{fighterData.fighter.record.draws}</Typography>
                        </Stack>
                            <Grid container spacing={3} justifyContent={{ mobile: 'center', laptop: 'flex-start' }}>
                                {/*Meta Data Box*/}
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                        <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                            <Typography variant="metaLabel" color="text.secondary">Height: </Typography>
                                            <Typography variant="metaText">{fighterData.fighter.height}"</Typography>
                                        </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Weight: </Typography>
                                        <Typography variant="metaText">{fighterData.fighter.weight}lbs</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Reach: </Typography>
                                        <Typography variant="metaText">{fighterData.fighter.reach}"</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Stance: </Typography>
                                        <Typography variant="metaText">{fighterData.fighter.stance}</Typography>
                                    </Stack>
                                </Grid>
                                <Grid size={{ mobile: 12, tablet: 6, laptop: 2.4 }}>
                                    <Stack direction="row" justifyContent={{mobile: "center", laptop: "flex-start"}} textAlign="center" spacing={.5}>
                                        <Typography variant="metaLabel" color="text.secondary">Dob: </Typography>
                                        <Typography variant="metaText">{fighterData.fighter.dob}</Typography>
                                    </Stack>
                                </Grid>
                            </Grid>
                            {/*Body Contents*/}
                            <Grid container spacing={0.5}>
                                {/*KPI Contents*/}
                                <Grid container size={12} spacing={1} sx={{ bgcolor: 'dashboardBlack.main', borderRadius: 2, p: 1}}>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">{slpm}</Typography>
                                            <Typography variant="caption">SLPM</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">{strDef}</Typography>
                                            <Typography variant="caption">Str. Def.</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">{strAcc}</Typography>
                                            <Typography variant="caption">Str. Acc.</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">{tdAcc}%</Typography>
                                            <Typography variant="caption">Td%</Typography>
                                        </Stack>
                                    </Grid>
                                    <Grid size={2.4} padding={1}>
                                        <Stack direction="column">
                                            <Typography variant="kpiValue">{tdDef}</Typography>
                                            <Typography variant="caption">Td Def.</Typography>
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
                                <Grid size={{mobile: 12, laptop: 5}}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2, overflow: 'hidden'}}>
                                        <WinLossChart record={winChartData}/>
                                    </Box>
                                </Grid>
                                {/*Past Fights List*/}
                                <Grid size={{mobile: 12, laptop: 7}}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2 }}>
                                           <DataGrid 
                                           columns={columns}
                                           rows={rows}
                                           hideFooter
                                           disableColumnSorting
                                           disableRowSelectionOnClick
                                            //Allows alternating colored rows
                                            getRowClassName={(params) =>
                                                params.indexRelativeToCurrentPage % 2 === 0 ? "even-row" : "odd-row"
                                            }
                                            // STYLING
                                            sx={(theme) => ({
                                                //Alternating row colors
                                                "& .MuiDataGrid-row.even-row":{
                                                    backgroundColor: (theme.palette.brand as any).dark,
                                                },
                                                "& .MuiDataGrid-row.odd-row":{
                                                    backgroundColor: "transparent",
                                                },

                                                //Text Styling     
                                                // Hides Unwanted parts of the grid
                                                // Sort Icons and Interactive elements from them
                                                "& .MuiDataGrid-iconButtonContainer": {display: "none"},
                                                "& .MuiDataGrid-sortIcon": {display: "none"},
                                            })} 
                                           />
                                    </Box>
                                </Grid>
                            </Grid>
                </Stack>
        </Container>
        
    )
}