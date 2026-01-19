import { Container, Stack, SxProps, Theme } from '@mui/material';
import { ReactNode } from "react";

export default function ListPageLayout(props: { children: ReactNode, sx?: SxProps<Theme> }) {
    return (
        <>
            <Container maxWidth="desktop" sx={{ ...props.sx }}>
                <Stack direction="column">
                    {props.children}
                </Stack>
            </Container>
        </>
    )
}