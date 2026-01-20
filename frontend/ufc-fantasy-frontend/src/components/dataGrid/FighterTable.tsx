import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Box, Button } from '@mui/material';


export interface FighterTableProps {
    variant?: 'default' | 'draft' | 'userTeam'; // Controls whats getting styled
    showStatus?: boolean; // Controls if "Status" column is shown
    hideFooter?: boolean;
}

// Mock Data 
export const MOCK_FIGHTER_ROWS = [
    { id: 1, weightClass: 'HW', fighter: 'Tom Aspinall', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 2, weightClass: 'HW', fighter: 'Jon Jones', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 3, weightClass: 'HW', fighter: 'Francis Ngannou', status: 'Free', last: 321, year: 172, average: 86, projected: 86 },
    { id: 4, weightClass: 'HW', fighter: 'Ciryl Gane', status: 'Susp', last: 321, year: 172, average: 86, projected: 86 },
    { id: 5, weightClass: 'HW', fighter: 'Sergei Pavlovich', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 6, weightClass: 'HW', fighter: 'Curtis Blaydes', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 7, weightClass: 'HW', fighter: 'Jailton Almeida', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 8, weightClass: 'HW', fighter: 'Alexander Volkov', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 9, weightClass: 'HW', fighter: 'Stipe Miocic', status: 'Ret.', last: 321, year: 172, average: 86, projected: 86 },
    { id: 10, weightClass: 'HW', fighter: 'Tai Tuivasa', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 11, weightClass: 'HW', fighter: 'Derrick Lewis', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 12, weightClass: 'HW', fighter: 'Marcos Rogerio', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 13, weightClass: 'HW', fighter: 'Marcos Rogerio', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 14, weightClass: 'HW', fighter: 'Marcos Rogerio', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 15, weightClass: 'HW', fighter: 'Marcos Rogerio', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },
    { id: 16, weightClass: 'HW', fighter: 'Marcos Rogerio', status: 'Booked', last: 321, year: 172, average: 86, projected: 86 },

];

export default function FighterTable({
    variant = 'default',
    showStatus = true,
    hideFooter = true
}: FighterTableProps) {

    // 1. Define Columns Logic
    const columns: GridColDef[] = [
        { field: 'weightClass', headerName: 'WC', flex: 0.5, minWidth: 50 },
        { field: 'fighter', headerName: 'Fighter', flex: 2, minWidth: 150 },

        // "Draft" Button visual (Only in draft mode)
        ...(variant === 'draft' ? [{
            field: 'actions',
            headerName: '',
            flex: 0.8,
            minWidth: 80,
            renderCell: (params: any) => (
                <Box sx={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                    <Button
                        variant="contained"
                        color="whiteAlpha20"
                        size="small"
                        sx={{
                            fontSize: '0.7rem',
                            minWidth: 'unset',
                            px: 1.5,
                            py: 0.5,
                            boxShadow: 'none',
                            '&:hover': { boxShadow: 'none' }
                        }}
                    >
                        Draft
                    </Button>
                </Box>
            )
        }] : []),

        // Conditionally add Status column
        ...(showStatus ? [{ field: 'status', headerName: 'Status', flex: 1, minWidth: 100 }] : []),

        { field: 'last', headerName: 'Last', flex: 0.5, minWidth: 60 },
        { field: 'year', headerName: 'Year', flex: 0.5, minWidth: 60 },
        { field: 'average', headerName: 'Avg', flex: 0.5, minWidth: 60 },
        { field: 'projected', headerName: 'Proj', flex: 0.5, minWidth: 60 },
    ];

    // 2. Define Styles based on Variant
    const getStyles = (theme: any) => {
        const styles = {
            border: 0,
            borderRadius: 8,

            // "Invisible" Borders logic from global theme
            "--DataGrid-rowBorderColor": "transparent",
            "--DataGrid-borderColor": "transparent",
            "--DataGrid-columnSeparatorColor": "transparent",
            "& .MuiDataGrid-columnSeparator": { opacity: 0 },

            // Default Colors (Mocking the "Normal" table look)
            backgroundColor: 'dashboardBlack.main',
            "& .MuiDataGrid-columnHeader": {
                backgroundColor: 'dashboardBlack.main',
                color: 'text.secondary',
                fontSize: '0.85rem'
            },
            "& .MuiDataGrid-columnHeaderTitle": {
                fontWeight: '300',
            },

            // Cleans up unwanted styling
            "& .MuiDataGrid-cell": { borderBottom: 'none' },
            "& ::-webkit-scrollbar": { display: 'none' },
        };

        // Draft Mode Specifics
        if (variant === 'draft') {
            return {
                ...styles,
                "& .MuiDataGrid-row.even-row": { backgroundColor: (theme.palette.brand as any).dark },
                "& .MuiDataGrid-row.odd-row": { backgroundColor: 'transparent' },
            };
        }

        // User Team Mode Specifics (from UserTeamPage.tsx logic)
        if (variant === 'userTeam') {
            return {
                ...styles,
                "& .MuiDataGrid-row.even-row": { backgroundColor: (theme.palette.brand as any).dark },
                "& .MuiDataGrid-row.odd-row": { backgroundColor: "transparent" },
                // Hide sort icons
                "& .MuiDataGrid-iconButtonContainer": { display: "none" },
                "& .MuiDataGrid-sortIcon": { display: "none" },
            };
        }

        return styles;
    };

    return (
        <DataGrid
            rows={MOCK_FIGHTER_ROWS}
            columns={columns}
            hideFooter={hideFooter}
            disableRowSelectionOnClick
            disableColumnMenu
            getRowClassName={(params) =>
                params.indexRelativeToCurrentPage % 2 === 0 ? "even-row" : "odd-row"
            }
            sx={(theme) => getStyles(theme)}
        />
    );
}
