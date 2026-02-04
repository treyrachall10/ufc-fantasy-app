import ListPageLayout from "../components/layout/ListPageLayout";
import { DataGrid } from '@mui/x-data-grid';
import { Box, Typography, Stack } from '@mui/material';
import { AuthContext } from "../auth/AuthProvider";
import { useContext } from "react";
import { useParams } from "react-router-dom";
import { authFetch } from "../auth/authFetch";
import { useQuery } from "@tanstack/react-query";

export interface TeamListFighter {
    fighter_id: number;
    full_name: string;
    weight: number;
}

export interface TeamFighterFantasyStats {
    last_fight_points: number;
    average_fight_points: number;
}

export interface TeamRosterSlot {
    slot: string;
    fighter: TeamListFighter | null;
    fantasy: TeamFighterFantasyStats | null;
}

export interface TeamDataResponse {
    team: {
        id: number;
        name: string;
        owner: string;
    };
    roster: TeamRosterSlot[];
}

export default function UserTeamPage() {
    const auth = useContext(AuthContext)!
    const params = useParams();

    const { data, isPending, error} = useQuery<TeamDataResponse>({
        queryKey: ['Team', params.teamid],
        queryFn: () => authFetch(`http://localhost:8000/team/${params.teamid}`).then(r => r.json()),
    })

    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns = [
        {field: 'weightClass', headerName: 'Weight Class', flex: 1, minWidth: 120},
        {field: 'fighter', headerName: 'Fighter', flex: 1.6, minWidth: 210}, //Flex keeps consistent sizing when chaning window size
        {field: 'status', headerName: 'Status', flex: 1.0, minWidth: 120},
        {field: 'projected', headerName: 'Projected', flex: 0.7, minWidth: 110},
        {field: 'year', headerName: 'Year', flex: 0.7, minWidth: 90},
        {field: 'average', headerName: 'Avg', flex: 0.6, minWidth: 80},
        {field: 'last', headerName: 'Last', flex: 1, minWidth: 80}
    ];
    
    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out fighters with long name

    const rows = data.roster.map((slot, index) => ({
        id: slot.fighter?.fighter_id || index,
        weightClass: slot.slot,
        fighter: slot.fighter?.full_name || 'Empty',
        status: 'Coming Soon',
        projected: 'Coming Soon',
        year: '2026',
        average: slot.fantasy ? slot.fantasy.average_fight_points.toFixed(1) : '0.0',
        last: slot.fantasy ? slot.fantasy.last_fight_points.toFixed(1) : '0.0',
    }))
    
    return (
        <ListPageLayout>

            {/* Stack formats vertical spacing between title and subtitle */}            
            <Stack spacing= {2} sx={{ mb: 3, width: "100%"}}>
              
                {/* Page title using h2 variant from theme */}
                <Typography variant = "h2" color= "text.primary"> 
                    {data.team.name}
                </Typography>

                {/* Subtitle with points and owner  - horizontal layout */}
                <Stack direction= "row" spacing= {1} alignItems= "baseline">
                    <Typography variant= "subtitle1" color= "text.secondary">
                        160 pts
                    </Typography>
                    <Typography variant= "body" color= "text.secondary">
                        |
                    </Typography>
                    <Typography variant= "body" color="text.secondary">
                        {data.team.owner}
                    </Typography>
                </Stack>
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
