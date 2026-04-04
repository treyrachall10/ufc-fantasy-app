import { useState } from 'react';
import ListPageLayout from "../components/layout/ListPageLayout";
import ListHeader from "../components/ListHeader";
import FightersList from "../components/lists/FightersList"

export default function FightersListPage() {
    const [typedSearch, setTypedSearch] = useState('');
    const [submittedSearch, setSubmittedSearch] = useState('');

    return (
        <ListPageLayout>
            <ListHeader
                title="Fighters"
                searchBarLabel="Search by fighter name"
                searchValue={typedSearch}
                onSearchChange={setTypedSearch}
                onSearchEnter={() => setSubmittedSearch(typedSearch)}
            ></ListHeader>
            <FightersList searchTerm={submittedSearch}></FightersList>
        </ListPageLayout>
    )
}