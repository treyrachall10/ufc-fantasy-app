import { Container, Grid, Box, Typography, Stack} from "@mui/material";
import { DataGrid } from '@mui/x-data-grid';
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

    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns = [
        {field: 'opponent', headerName: 'Opponent', flex: 1},
        {field: 'event', headerName: 'Event', flex: 1 }, //Flex keeps consistent sizing when chaning window size
        {field: 'round', headerName: 'Round', flex: 1 },
        {field: 'date', headerName: 'Date', flex: 1},
    ];
    
    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out events with long name
    const rows = [
    {
        id: 1,
        opponent: 'Alex Pereira',
        event: 'UFC 281',
        round: 'R5 (KO)',
        date: '2022-11-12',
    },
    {
        id: 2,
        opponent: 'Robert Whittaker',
        event: 'UFC 271',
        round: 'Decision',
        date: '2022-02-12',
    },
    {
        id: 3,
        opponent: 'Paulo Costa',
        event: 'UFC 253',
        round: 'R2 (TKO)',
        date: '2020-09-26',
    },
    {
        id: 4,
        opponent: 'Kelvin Gastelum',
        event: 'UFC 236',
        round: 'Decision',
        date: '2019-04-13',
    },
    {
        id: 5,
        opponent: 'Derek Brunson',
        event: 'UFC 230',
        round: 'R1 (TKO)',
        date: '2018-11-03',
    },
    {
        id: 6,
        opponent: 'Anderson Silva',
        event: 'UFC 234',
        round: 'Decision',
        date: '2019-02-10',
    },
    {
        id: 7,
        opponent: 'Jared Cannonier',
        event: 'UFC 276',
        round: 'Decision',
        date: '2022-07-02',
    },
    ];

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
                            <Grid container spacing={0.5}>
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
                                <Grid size={{mobile: 12, laptop: 5}}>
                                    <Box sx={{ height: 400, bgcolor: 'dashboardBlack.main', borderRadius: 2, overflow: 'hidden'}}>
                                        <WinLossChart record={mockData}/>
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