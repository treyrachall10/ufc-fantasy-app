import { TextField } from '@mui/material';
import Stack from '@mui/material/Stack';

interface ListHeaderProps {
    title: string;
    searchBarLabel: string;
    searchValue?: string;
    onSearchChange?: (value: string) => void;
}

export default function ListHeader(props: ListHeaderProps) {
    return (
        <Stack direction="row" justifyContent={'space-between'} alignItems={'center'}>
            <h2>{props.title}</h2>
            <TextField 
                id="outlined-basic" 
                label={props.searchBarLabel} 
                variant="outlined"
                value={props.searchValue || ""}
                onChange={(e) => props.onSearchChange?.(e.target.value)}
                placeholder="Type to search..."
            />
        </Stack>
    )
}