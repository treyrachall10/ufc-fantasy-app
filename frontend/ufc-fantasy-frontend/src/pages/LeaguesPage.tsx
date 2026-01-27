import ListPageLayout from "../components/layout/ListPageLayout";
import { DataGrid } from '@mui/x-data-grid';
import { Box, Typography, Stack } from '@mui/material';
import { Link, Button } from '@mui/material';
import { Router, Link as RouterLink} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { authFetch } from "../auth/authFetch";

interface UserLeaguesAndTeams {
    league_id: number,
    league_name: string,
    team_id: number,
    team_name: string
}

export default function LeaguesPage() {

    const { data, isPending, error} = useQuery<UserLeaguesAndTeams[]>({
        queryKey: ['userLeaguesAndTeams'],
        queryFn: () => authFetch(`http://localhost:8000/leagues`).then(r => r.json()),
    })

    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns = [
        { field: 'league', headerName: 'League', renderCell: (params: any) => (
            <Link 
                href={`/league/${params.id}`} 
                sx={{
                    textDecoration: 'underline',
                    color: 'text.primary'
                }}
                >{params.value}</Link>
        ), flex: 1 },
        { field: 'team', headerName: 'Team', renderCell: (params: any) => (
            <Link 
                href={`/team/${params.team_id}`} 
                sx={{
                    textDecoration: 'underline',
                    color: 'text.primary'
                }}
                >{params.value}</Link>
        ),flex: 1 },
        { field: 'points', headerName: 'Points', flex: 1 },
        { field: 'standing', headerName: 'Standing', flex: 1 },
    ];

    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out fighters with long name
    const rows = data.map((data) => ({
        id: data.league_id,
        league: data.league_name,
        team: data.team_name,
        team_id: data.team_id,
        points: 200,
        standing: '1'
    }))

    // Turn league standings numbers to string
    for (const row of rows) {
        if (row.standing === '1') {
            row.standing = '1st Place';
        } else if (row.standing === '2') {
            row.standing = '2nd Place';
        } else if (row.standing === '3') {
            row.standing = '3rd Place';
        } else {
            row.standing = `${row.standing}th Place`;
        }
    }

    return (
        <ListPageLayout>

            {/* Stack formats vertical spacing between title and subtitle */}            
            <Stack 
                direction={{xs: 'column', lg: 'row'}}
                spacing={{xs: 2, lg: 0}}
                sx={{ 
                        mb: 3, 
                        width: "100%",
                        alignItems: 'center',
                        justifyContent: 'space-between'
                    }}
                >
                {/* Page title using h2 variant from theme */}
                <Typography variant = "h2" color= "text.primary"> 
                    Your Leagues
                </Typography>
                <Box 
                sx={{
                    display: 'flex',
                    flexDirection: {xs: 'column', lg: 'row'},
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 1
                }}>
                    <Button 
                            variant="contained" 
                            color='brandAlpha50'
                            component={RouterLink} to='/join'
                            sx={{ 

                                borderColor: 'brand.light',
                                '&:hover': {
                                    borderColor: 'brand.main'
                                }                        
                            }}
                        >
                            Join a League
                    </Button>
                    <Button 
                        variant="contained" 
                        color="whiteAlpha20"
                        component={RouterLink} to="/leagues/create-league"
                        sx={{

                            borderColor: 'gray900.main',
                            '&:hover': {
                                borderColor: 'gray800.main'
                            }
                        }}
                    >
                        Create League
                    </Button>
                </Box>
            </Stack>
            <Box sx={{ width: '100%', overflow: "hidden" }}>
                <DataGrid //displays the table 
                    rows= {rows} 
                    columns= {columns} 
                    hideFooter 
                    disableRowSelectionOnClick // removes checkboxes
                    disableVirtualization // renders all rows on a page, prevents scrolling the grid to see rows
                    disableColumnSorting // removes sorting. (if adding filtering remove this)
                    
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
        </ListPageLayout>
    )
}
