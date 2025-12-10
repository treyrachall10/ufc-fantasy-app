import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';

export default function FightersList() {
    const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', renderCell: (params) => (
        <Link to="/fighter" style={{color: "black"}}>{params.value}</Link>
    )},
    { field: 'w', headerName: 'W' },
    { field: 'l', headerName: 'L' },
    ];

    const rows = [
    { id: 1, name: "Conor McGregor", w: 22, l: 6 },
    { id: 2, name: "Jon Jones", w: 27, l: 1 },
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}