import { TextField } from '@mui/material';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Stack from '@mui/material/Stack';
import SearchIcon from '@mui/icons-material/Search';
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
                sx={{bgcolor: 'black'}}
                slotProps={{
                    input: {
                        endAdornment: (
                            <InputAdornment position="end" sx={{bgcolor: 'black'}}>
                                <IconButton
                                    aria-label="search fighters"
                                    onClick={() => props.onSearchEnter?.()}
                                    edge="end"
                                    sx={{bgcolor: 'black'}}
                                >
                                    <SearchIcon sx={{ color: 'common.white' }} />
                                </IconButton>
                            </InputAdornment>
                        ),
                    },
                }}
            ></TextField>
        </Stack>
    )
}