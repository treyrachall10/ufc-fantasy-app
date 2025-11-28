import { Container} from '@mui/material';
import Stack from '@mui/material/Stack';
import { ReactNode } from "react";

export default function ListPageLayout (props: { children: ReactNode }) {
    return (
    <>
        <Container maxWidth="lg">
            <Stack direction="column">
                {props.children}
            </Stack>
        </Container>
    </>
    )
}