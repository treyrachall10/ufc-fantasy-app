import { useState } from 'react';
import { DataGrid, GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query'
import { Fighter, PaginatedResponse } from '../../types/types';

export default function FightersList() {
    const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
    const { page, pageSize } = paginationModel;

    {/* API fetching*/}    
    const { data, isPending, error } = useQuery<PaginatedResponse<Fighter>>({
        queryKey: ['fighterListData', page, pageSize],
        queryFn: () => fetch(`http://localhost:8000/fighters/?page=${page + 1}&page_size=${pageSize}`).then(r => r.json()),
    });
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const columns: GridColDef[] = [
    {
        field: 'name',
        headerName: 'Name',
        flex: 2,
        renderCell: (params) => (
        <Link to={`/fighter/${params.id}`} style={{ color: 'white' }}>
            {params.value}
        </Link>
        ),
    },
    { field: 'nickName', headerName: 'Nick Name', flex: 1 },
    { field: 'stance', headerName: 'Stance', flex: 1 },
    { field: 'weight', headerName: 'Weight', flex: 1 },
    { field: 'height', headerName: 'Height', flex: 1 },
    { field: 'reach', headerName: 'Reach', flex: 1 },
    { field: 'dob', headerName: 'DOB', flex: 1 },
    { field: 'w', headerName: 'W', flex: 0.5 },
    { field: 'l', headerName: 'L', flex: 0.5 },
    { field: 'd', headerName: 'D', flex: 0.5 },
    ];

    const rows = data.results.map((fighter) => ({
        id: fighter.fighter_id,
        name: fighter.full_name,
        nickName: fighter.nick_name,
        stance: fighter.stance,
        weight: fighter.weight,
        height: fighter.height,
        reach: fighter.reach,
        dob: fighter.dob,
        w: fighter.record?.wins.total,
        l: fighter.record?.losses.total,
        d: fighter.record?.draws,
    }));

    return(
        <DataGrid 
            columns={columns}
            rows={rows}
            rowCount={data.count}
            paginationMode="server"
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            disableColumnSorting
            disableRowSelectionOnClick
            disableColumnMenu
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
    )
}