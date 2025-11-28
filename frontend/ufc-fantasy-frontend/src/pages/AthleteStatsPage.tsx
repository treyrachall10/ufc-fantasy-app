import { Container, Grid, Box } from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import QuickStatCard from "../components/statHolders/QuickStatCard";
import FightsList from "../components/lists/FightsList";
import WinLossChart from "../components/charts/WinLossChart";
import FantasyTrendLineChart from "../components/charts/FantasyTrendLineChart";

interface Fighter {
    name: string;
    nickname?: string;
  
    // Bio / Profile
    stance?: string;
    age: number;
    height: number;
    weight: number;
    reach: number;
  
    // Record
    w: number;
    l: number;
    d: number;
  
    // Stats
    kd: number;
    sig_str_landed: number;
    sig_str_attempted: number;
    total_str_landed: number;
    total_str_attempted: number;
    td_landed: number;
    td_attempted: number;
    sub_att: number;
    ctrl_time: number;
    reversals: number;
    head_str_landed: number;
    head_str_attempted: number;
    body_str_landed: number;
    body_str_attempted: number;
    leg_str_landed: number;
    leg_str_attempted: number;
    distance_str_landed: number;
    distance_str_attempted: number;
    clinch_str_landed: number;
    clinch_str_attempted: number;
    ground_str_landed: number;
    ground_str_attempted: number;
    total_fights: number;
    dq: number;
    majority_decisions: number;
    split_decisions: number;
    unanimous_decisions: number;
    ko_tko: number;
    submissions: number;
    tko_doctor_stoppages: number;
  }
  

export default function AthleteStatsPage({fighter}: {fighter: Fighter}){
    const SLPM = 0;
    const TD_DEF = 0;
    const STR_ACC = 0;
    const TD_ACC = 0;
    const STR_DEF = 0;

    return (
        <Container>
            <Grid container spacing={2}>

                {/* Sidebar */}
                <Grid size={{ xs: 12, md: 2}}>
                    <Sidebar 
                        name={fighter.name}
                        nickname={fighter.nickname}
                        age={fighter.age}
                        height={fighter.height}
                        weight={fighter.weight}
                        reach={fighter.reach}
                        stance={fighter.stance}
                        w={fighter.w}
                        l={fighter.l}
                        d={fighter.d}
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
                                <QuickStatCard title="SLPM" stat={SLPM}/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD%" stat={TD_DEF} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR ACC" stat={STR_ACC} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="TD ACC" stat={TD_ACC} />
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 4, lg: 2}}>
                                <QuickStatCard title="STR DEF" stat={STR_DEF} />
                            </Grid>
                        </Grid>
                        {/* Fantsy Chart and W/L Chart */}
                        <Grid container spacing={2}>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <FantasyTrendLineChart/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <WinLossChart/>
                            </Grid>
                        </Grid>
                        {/* FightList and Interesting Stats */}
                        <Grid container spacing={2}>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <FightsList/>
                            </Grid>
                            <Grid size={{xs: 12, sm: 6, md: 6, lg: 6}}>
                                <QuickStatCard title="Control %" stat={32} />
                            </Grid>
                        </Grid>
                    </Box>
                </Grid>
            </Grid>
        </Container>
        
    )
}