import { Search } from "lucide-react"; 
 
export default function SearchPage() { 
  return ( 
    <div className="flex flex-col items-center justify-center h-96 gap-4 text-center"> 
      <Search className="w-12 h-12 text-white/20" /> 
      <h1 className="text-2xl font-bold text-white">Search Transcripts</h1> 
      <p className="text-white/40 max-w-sm"> 
        Full-text transcript search is coming in V2 with Elasticsearch integration. 
      </p> 
    </div> 
  ); 
}
