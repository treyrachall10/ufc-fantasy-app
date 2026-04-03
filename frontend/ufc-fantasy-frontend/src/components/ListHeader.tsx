import { TextField } from '@mui/material';
import Stack from '@mui/material/Stack';
import { KeyboardEvent } from 'react';

interface ListHeaderProps {
    title: string;
    searchBarLabel: string;
    searchValue?: string;
    onSearchChange?: (value: string) => void;
    onSearchEnter?: () => void;
}

export default function ListHeader(props: ListHeaderProps) {
    const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            props.onSearchEnter?.();
        }
    };

    return (
        <Stack direction="row" justifyContent={'space-between'} alignItems={'center'}>
            <h2>{props.title}</h2>
            <TextField
                id="outlined-basic"
                label={props.searchBarLabel}
                variant="outlined"
                value={props.searchValue ?? ''}
                onChange={(event) => props.onSearchChange?.(event.target.value)}
                onKeyDown={handleKeyDown}
            ></TextField>
        </Stack>
    )
}