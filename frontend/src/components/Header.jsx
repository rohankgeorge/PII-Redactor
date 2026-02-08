import { ShieldCheck, Info, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const PII_TYPES = [
  "Aadhaar Numbers",
  "PAN Numbers",
  "Phone Numbers",
  "Email Addresses",
  "Passport Numbers",
  "Voter IDs",
  "IFSC Codes",
  "GST Numbers",
  "UPI IDs",
  "Driving Licenses",
  "Vehicle Registrations",
  "Bank Accounts",
  "Addresses & PIN Codes",
  "Indian Names",
  "Indian Locations",
  "Dates of Birth",
];

export default function Header() {
  return (
    <header className="border-b border-border/60 backdrop-blur-sm" data-testid="app-header">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-7 h-7 text-primary" strokeWidth={1.5} />
          <span className="text-xl font-heading font-bold tracking-tight text-foreground">
            RedactAI
          </span>
          <Badge variant="secondary" className="hidden sm:inline-flex text-[11px] tracking-wide" data-testid="client-badge">
            Client-Side Processing
          </Badge>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground" data-testid="pii-types-dropdown">
              <Info className="w-4 h-4" strokeWidth={1.5} />
              <span className="hidden sm:inline text-sm">PII Types</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Detected PII Categories</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {PII_TYPES.map((t) => (
              <DropdownMenuItem key={t} className="text-sm text-muted-foreground">
                {t}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
