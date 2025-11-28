import { DataGrid, GridColDef } from '@mui/x-data-grid';

export default function FightersList() {
    const columns: GridColDef[] = [
    { field: 'first', headerName: 'First' },
    { field: 'last', headerName: 'Last' },
    { field: 'w', headerName: 'W' },
    { field: 'l', headerName: 'L' },
    ];

    const rows = [
    { id: 1, first: "Conor", last: "McGregor", w: 22, l: 6 },
    { id: 2, first: "Jon", last: "Jones", w: 27, l: 1 },
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}