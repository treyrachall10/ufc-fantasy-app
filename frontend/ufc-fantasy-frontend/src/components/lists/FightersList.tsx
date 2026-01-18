import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query'
import { Fighter } from '../../types/types';
import { getToken } from '../../auth/auth';
import { authFetch } from '../../auth/authFetch';

export default function FightersList() {      
    {/* API fetching*/}    
    const { data, isPending, error } = useQuery<Fighter[]>({
        queryKey: ['fighterListData'],
        queryFn: () => fetch('http://localhost:8000/fighters').then(r => r.json()),

    });
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', renderCell: (params) => (
        <Link to={`/fighter/${params.id}`} style={{color: "black"}}>{params.value}</Link>
    )},
    { field: 'nickName', headerName: 'Nick Name' },
    { field: 'stance', headerName: 'stance' },
    { field: 'weight', headerName: 'Weight' },
    { field: 'height', headerName: 'Height' },
    { field: 'reach', headerName: 'Reach' },
    { field: 'dob', headerName: 'DOB' },
    { field: 'w', headerName: 'W' },
    { field: 'l', headerName: 'L' },
    { field: 'd', headerName: 'D' },
    ];

    const rows = data.map((fighter) => ({
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
        <DataGrid columns={columns} rows={rows}/>
    )
}