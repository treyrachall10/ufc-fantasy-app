import ListPageLayout from "../components/layout/ListPageLayout";
import ListHeader from "../components/ListHeader";
import FightersList from "../components/lists/FightersList"
import { useState } from "react";

export default function FightersListPage() {
    const [searchQuery, setSearchQuery] = useState("");

    return (
        <ListPageLayout>
            <ListHeader 
                title="Fighters" 
                searchBarLabel="Search by fighter name"
                searchValue={searchQuery}
                onSearchChange={setSearchQuery}
            />
            <FightersList searchQuery={searchQuery} />
        </ListPageLayout>
    )
}