import { useEffect, useState } from 'react';
import { DataGrid, GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query'
import { Fighter, PaginatedResponse } from '../../types/types';
import { Avatar, Box } from '@mui/material';

interface FightersListProps {
    searchTerm?: string;
}

export default function FightersList({ searchTerm = '' }: FightersListProps) {
    const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
    const { page, pageSize } = paginationModel;

    useEffect(() => {
        setPaginationModel((prev) => ({ ...prev, page: 0 }));
    }, [searchTerm]);

    const { data, isPending, error } = useQuery<PaginatedResponse<Fighter>>({
        queryKey: ['fighterListData', page, pageSize, searchTerm],
        queryFn: () => {
            const params = new URLSearchParams({
                page: String(page + 1),
                page_size: String(pageSize),
            });

            if (searchTerm) {
                params.set('search', searchTerm);
            }

            return fetch(`http://localhost:8000/fighters/?${params.toString()}`).then(r => r.json());
        },
    });
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const columns: GridColDef[] = [
    {
        field: 'name',
        headerName: 'Name',
        flex: 2,
        renderCell: (params) => (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar src={params.row.img_url || undefined} alt={params.value} sx={{ marginRight: 1 }} />
                <Link to={`/fighter/${params.id}`} style={{ color: 'white' }}>
                    {params.value}
                </Link>
            </Box>
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
        img_url: fighter.img_url,
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