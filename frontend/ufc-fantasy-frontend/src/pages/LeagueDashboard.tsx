import ListPageLayout from "../components/layout/ListPageLayout";
import Avatar from '@mui/material/Avatar';
import { Box, Typography, Stack, Grid } from '@mui/material';
import Link from '@mui/material/Link';
import LeagueStandingsBarChart from "../components/charts/LeagueStandingsBarChart";
import LeagueStandingBarChartLabel from "../components/badges/LeagueStandingBarChartLabel";

export default function LeagueDashboard() {
    const data = [
        { team: "Iron Fist FC", pts: 184, standing: 0 },
        { team: "Bloodline MMA", pts: 162, standing: 0 },
        { team: "Apex Predators", pts: 201, standing: 0 },
        { team: "Submission Syndicate", pts: 139, standing: 0 },
        { team: "Knockout Kings", pts: 225, standing: 0 },
        { team: "Ground Zero Gym", pts: 121, standing: 0 },
        { team: "Warpath Fight Team", pts: 173, standing: 0 },
    ];
    // Compute league standing
    for (const team of data) {
        let standing = 1;
        for (const comparingTeam of data) {
            if (team.pts < comparingTeam.pts) {
                standing +=1;
            }
        }
        team.standing = standing;
    }

    return (
        <ListPageLayout>
            <Grid
                container 
                spacing={1} 
                sx={{
                    display: 'flex',
                    justifyContent: {xs: 'center', md: 'space-between'},
                }}>
                <Grid 
                    size={{xs: 6, md: 8}}
                    sx={{
                        display: 'flex'
                    }}
                    >
                    {/* Stack formats vertical spacing between title and subtitle */}            
                    <Stack spacing= {2} >
                        <Stack spacing={1}>
                            {/* Page title using h2 variant from theme */}
                            <Typography 
                                variant = "h2" 
                                color= "text.primary"
                                sx={{
                                    lineHeight: {xs: '1.7rem', md: '1.1rem'}
                                }}
                                > 
                                League Name
                            </Typography>
                            {/* Subtitle */}
                            <Stack direction= {{xs: "column", md: "row"}} spacing= {1} alignItems= "baseline">
                                <Typography variant= "subtitle1" color= "text.secondary">
                                    8 Teams
                                </Typography>
                                <Typography variant= "body" color="text.secondary">
                                    League Owner
                                </Typography>
                            </Stack>
                        </Stack>
                        <Box>
                            <Link sx={{fontSize: "1.25rem", color: 'hsla(198, 100%, 58%, 0.5)'}}>Scoring Criteria</Link>
                        </Box>
                    </Stack>
                </Grid>
                {/* League Image*/}
                <Grid size={{xs: 6, sm: 4}}>
                    <Box 
                        sx={{
                            display: 'flex',
                            height: '100%',
                            justifyContent: 'center',
                            alignItems: 'center',
                        }}
                    >
                        <Avatar 
                            alt="League Image" 
                            sx={{ 
                                bgcolor: 'red',
                                height: {xs: 128, lg: 256},
                                width: {xs: 128, lg: 256}
                            }}
                            >
                            B
                        </Avatar>
                    </Box>
                </Grid>
                {/* League Standings Chart*/}
                <Grid 
                    size={{mobile: 12}}
                    sx={{
                        borderRadius: 2,
                        overflow: 'hidden',
                        position: 'relative',
                    }}
                    >
                        <Box display={{xs: 'none', lg: 'block'}}>
                        <LeagueStandingsBarChart/>
                        {/* Custom Overlaying Chart Labels */}
                        <Box
                            sx={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                height: '100%',
                                bgcolor: 'dashboardBlack.main',
                                pl: 3,
                                pt: 2,
                                pb: 4,
                            }}>
                                <Typography 
                                sx={{
                                    fontSize: '1rem',
                                    lineHeight: '1.3rem',
                                    letterSpacing: '0.01em',
                                    fontWeight: 500,
                                    color: 'hsla(0, 0%, 20%, 1)',
                                }}>
                                    Standings
                                </Typography>
                                <LeagueStandingBarChartLabel teams={data}/> {/* Creates continer of labels */}
                                </Box>
                        </Box>
                </Grid>
            </Grid>
        </ListPageLayout>
    )
}