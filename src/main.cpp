#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr const char* HEADER = "id,name,category,last_serviced,service_interval_days,hours_since_service,max_hours_between_service";
constexpr int SOON_DAYS = 14;
constexpr int SOON_HOURS = 50;

struct Asset {
    std::string id, name, category, last_serviced;
    int interval_days{}, hours_since_service{}, hour_limit{};
};

struct Assessment {
    int remaining_days{}, remaining_hours{};
    std::string status, due_date;
};

int parse_int(const std::string& text, const std::string& field) {
    try {
        std::size_t end{};
        int n = std::stoi(text, &end);
        if (end != text.size()) throw std::invalid_argument("trailing text");
        return n;
    } catch (const std::exception&) {
        throw std::runtime_error("Invalid integer for " + field + ": " + text);
    }
}

bool leap(int year) { return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0); }

struct Date { int year{}, month{}, day{}; };
Date parse_date(const std::string& value) {
    if (value.size() != 10 || value[4] != '-' || value[7] != '-')
        throw std::runtime_error("Date must use YYYY-MM-DD: " + value);
    for (std::size_t i = 0; i < value.size(); ++i)
        if (i != 4 && i != 7 && !std::isdigit(static_cast<unsigned char>(value[i])))
            throw std::runtime_error("Invalid date: " + value);
    Date d{std::stoi(value.substr(0, 4)), std::stoi(value.substr(5, 2)), std::stoi(value.substr(8, 2))};
    static const int days_in_month[] = {0,31,28,31,30,31,30,31,31,30,31,30,31};
    if (d.year < 1900 || d.year > 2100 || d.month < 1 || d.month > 12)
        throw std::runtime_error("Invalid date: " + value);
    int max_day = days_in_month[d.month] + (d.month == 2 && leap(d.year) ? 1 : 0);
    if (d.day < 1 || d.day > max_day) throw std::runtime_error("Invalid date: " + value);
    return d;
}

// Gregorian calendar date arithmetic (timezone-independent), derived from
// the public-domain civil-calendar algorithms by Howard Hinnant.
int days_from_civil(Date date) {
    int y = date.year - (date.month <= 2);
    int era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = static_cast<unsigned>(y - era * 400);
    unsigned m = static_cast<unsigned>(date.month);
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + static_cast<unsigned>(date.day) - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + static_cast<int>(doe) - 719468;
}

Date civil_from_days(int z) {
    z += 719468;
    int era = (z >= 0 ? z : z - 146096) / 146097;
    unsigned doe = static_cast<unsigned>(z - era * 146097);
    unsigned yoe = (doe - doe/1460 + doe/36524 - doe/146096) / 365;
    int y = static_cast<int>(yoe) + era * 400;
    unsigned doy = doe - (365*yoe + yoe/4 - yoe/100);
    unsigned mp = (5*doy + 2) / 153;
    unsigned d = doy - (153*mp+2)/5 + 1;
    int m = static_cast<int>(mp) + (mp < 10 ? 3 : -9);
    y += (m <= 2);
    return {y, m, static_cast<int>(d)};
}

std::string format_date(Date date) {
    std::ostringstream out;
    out << std::setfill('0') << std::setw(4) << date.year << '-'
        << std::setw(2) << date.month << '-' << std::setw(2) << date.day;
    return out.str();
}

std::vector<std::string> parse_csv_line(const std::string& line) {
    std::vector<std::string> result;
    std::string current;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        char ch = line[i];
        if (ch == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
                current.push_back('"'); ++i;
            } else quoted = !quoted;
        } else if (ch == ',' && !quoted) {
            result.push_back(current); current.clear();
        } else {
            current.push_back(ch);
        }
    }
    if (quoted) throw std::runtime_error("Malformed CSV: unmatched quote");
    result.push_back(current);
    return result;
}

std::string csv_escape(const std::string& text) {
    if (text.find_first_of(",\n\r\"") == std::string::npos) return text;
    std::string out = "\"";
    for (char ch : text) {
        if (ch == '"') out += '"';
        out += ch;
    }
    return out + '"';
}

void validate_asset(const Asset& a) {
    if (a.id.empty() || a.name.empty() || a.category.empty())
        throw std::runtime_error("Asset id, name and category must not be empty");
    for (const std::string* part : {&a.id, &a.name, &a.category})
        if (part->find_first_of("\r\n") != std::string::npos)
            throw std::runtime_error("Asset text must not contain a new line");
    parse_date(a.last_serviced);
    if (a.interval_days <= 0 || a.hour_limit <= 0 || a.hours_since_service < 0)
        throw std::runtime_error("Intervals must be positive and hours used nonnegative");
}

std::vector<Asset> load_assets(const std::string& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Cannot open data file: " + path);
    std::string line;
    if (!std::getline(file, line) || line != HEADER)
        throw std::runtime_error("Unexpected CSV header in " + path);
    std::vector<Asset> assets;
    std::size_t lineno = 1;
    while (std::getline(file, line)) {
        ++lineno;
        if (line.empty()) continue;
        auto cells = parse_csv_line(line);
        if (cells.size() != 7) throw std::runtime_error("Expected 7 CSV columns on line " + std::to_string(lineno));
        Asset a{cells[0], cells[1], cells[2], cells[3], parse_int(cells[4], "service_interval_days"),
                parse_int(cells[5], "hours_since_service"), parse_int(cells[6], "max_hours_between_service")};
        validate_asset(a);
        if (std::any_of(assets.begin(), assets.end(), [&](const Asset& existing){ return existing.id == a.id; }))
            throw std::runtime_error("Duplicate asset id: " + a.id);
        assets.push_back(a);
    }
    return assets;
}

void save_assets(const std::string& path, const std::vector<Asset>& assets) {
    // Write a complete temporary file, then replace the original.
    std::string tmp = path + ".tmp";
    {
        std::ofstream out(tmp, std::ios::trunc);
        if (!out) throw std::runtime_error("Cannot write data file: " + tmp);
        out << HEADER << '\n';
        for (const auto& a : assets) {
            out << csv_escape(a.id) << ',' << csv_escape(a.name) << ',' << csv_escape(a.category) << ','
                << a.last_serviced << ',' << a.interval_days << ',' << a.hours_since_service << ',' << a.hour_limit << '\n';
        }
        if (!out) throw std::runtime_error("Failed writing data file: " + tmp);
    }
    // A same-directory filesystem rename replaces the original on common filesystems.
    // This is a learning prototype; production use requires transaction and lock handling.
    try {
        std::filesystem::rename(tmp, path);
    } catch (const std::filesystem::filesystem_error& ex) {
        std::filesystem::remove(tmp);
        throw std::runtime_error("Could not safely replace data file: " + std::string(ex.what()));
    }
}

Assessment assess(const Asset& a, const std::string& as_of) {
    int service_day = days_from_civil(parse_date(a.last_serviced));
    int current_day = days_from_civil(parse_date(as_of));
    int left_days = (service_day + a.interval_days) - current_day;
    int left_hours = a.hour_limit - a.hours_since_service;
    std::string status = (left_days < 0 || left_hours < 0) ? "OVERDUE" :
        (left_days <= SOON_DAYS || left_hours <= SOON_HOURS) ? "DUE_SOON" : "OK";
    return {left_days, left_hours, status, format_date(civil_from_days(service_day + a.interval_days))};
}

int ranking(const std::string& s) { return s == "OVERDUE" ? 0 : (s == "DUE_SOON" ? 1 : 2); }

void help() {
    std::cout << "MineOps Asset Planner (synthetic demonstration project)\n\n"
              << "Usage: assetops <command> [args] [--file PATH] [--as-of YYYY-MM-DD]\n"
              << "Commands:\n"
              << "  list                   List all assets by maintenance priority\n"
              << "  summary                Print status totals\n"
              << "  due [--within N]       Show overdue/soon-due assets (default 14 days)\n"
              << "  export --output PATH   Export maintenance assessment as a CSV report\n"
              << "  add --id ID --name TEXT --category TEXT --last-serviced DATE\n"
              << "      --interval-days N --hours-used N --hour-limit N\n"
              << "  service ID --date YYYY-MM-DD   Mark asset serviced (hours reset)\n\n"
              << "Defaults: --file data/assets.csv, --as-of 2026-11-19 (reproducible demo)\n";
}

std::string option(const std::vector<std::string>& args, const std::string& key, const std::string& default_value = "") {
    for (std::size_t i = 0; i < args.size(); ++i) {
        if (args[i] == key) {
            if (i + 1 >= args.size() || (args[i + 1].rfind("--", 0) == 0))
                throw std::runtime_error("Missing value for " + key);
            return args[i + 1];
        }
    }
    return default_value;
}
std::string required_option(const std::vector<std::string>& args, const std::string& key) {
    auto value = option(args, key);
    if (value.empty()) throw std::runtime_error("Missing required option " + key);
    return value;
}

void print_table(const std::vector<Asset>& assets, const std::string& as_of, bool due_only, int within) {
    struct Row { Asset asset; Assessment outcome; };
    std::vector<Row> rows;
    for (const auto& asset : assets) {
        auto outcome = assess(asset, as_of);
        if (!due_only || outcome.status == "OVERDUE" || outcome.remaining_days <= within || outcome.remaining_hours <= SOON_HOURS)
            rows.push_back({asset, outcome});
    }
    std::sort(rows.begin(), rows.end(), [](const Row& a, const Row& b) {
        if (ranking(a.outcome.status) != ranking(b.outcome.status))
            return ranking(a.outcome.status) < ranking(b.outcome.status);
        if (a.outcome.remaining_days != b.outcome.remaining_days)
            return a.outcome.remaining_days < b.outcome.remaining_days;
        return a.asset.id < b.asset.id;
    });
    std::cout << "Maintenance status as of " << as_of << "\n"
              << std::left << std::setw(7) << "ID" << std::setw(27) << "ASSET"
              << std::setw(12) << "STATUS" << std::setw(14) << "DUE DATE"
              << std::right << std::setw(12) << "DAYS LEFT" << std::setw(13) << "HOURS LEFT" << '\n'
              << std::string(85, '-') << '\n';
    for (const auto& row : rows) {
        std::cout << std::left << std::setw(7) << row.asset.id
                  << std::setw(27) << row.asset.name.substr(0, 26)
                  << std::setw(12) << row.outcome.status
                  << std::setw(14) << row.outcome.due_date
                  << std::right << std::setw(12) << row.outcome.remaining_days
                  << std::setw(13) << row.outcome.remaining_hours << '\n';
    }
    std::cout << "Total: " << rows.size() << " asset(s)\n";
}

void export_csv(const std::vector<Asset>& assets, const std::string& path, const std::string& as_of) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Cannot write report: " + path);
    out << "id,name,category,last_serviced,service_due,days_remaining,hours_remaining,status\n";
    for (const auto& a : assets) {
        Assessment result = assess(a, as_of);
        out << csv_escape(a.id) << ',' << csv_escape(a.name) << ',' << csv_escape(a.category) << ','
            << a.last_serviced << ',' << result.due_date << ',' << result.remaining_days << ','
            << result.remaining_hours << ',' << result.status << '\n';
    }
    if (!out) throw std::runtime_error("Error writing report: " + path);
    std::cout << "Exported " << assets.size() << " assets to " << path << " (as of " << as_of << ")\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2 || std::string(argv[1]) == "--help" || std::string(argv[1]) == "help") {
            help(); return 0;
        }
        const std::string command = argv[1];
        std::vector<std::string> args(argv + 2, argv + argc);
        auto input_file = option(args, "--file", "data/assets.csv");
        auto as_of = option(args, "--as-of", "2026-11-19");
        parse_date(as_of);
        auto assets = load_assets(input_file);
        if (command == "list") {
            print_table(assets, as_of, false, SOON_DAYS);
        } else if (command == "summary") {
            int overdue = 0, due_soon = 0, okay = 0;
            for (const auto& asset : assets) {
                const auto status = assess(asset, as_of).status;
                if (status == "OVERDUE") ++overdue;
                else if (status == "DUE_SOON") ++due_soon;
                else ++okay;
            }
            std::cout << "Maintenance summary as of " << as_of << '\n'
                      << "Assets:    " << assets.size() << '\n'
                      << "Overdue:   " << overdue << '\n'
                      << "Due soon:  " << due_soon << '\n'
                      << "OK:        " << okay << '\n';
        } else if (command == "due") {
            int within = parse_int(option(args, "--within", "14"), "--within");
            if (within < 0) throw std::runtime_error("--within must be nonnegative");
            print_table(assets, as_of, true, within);
        } else if (command == "export") {
            export_csv(assets, required_option(args, "--output"), as_of);
        } else if (command == "add") {
            Asset asset{required_option(args, "--id"), required_option(args, "--name"),
                        required_option(args, "--category"), required_option(args, "--last-serviced"),
                        parse_int(required_option(args, "--interval-days"), "--interval-days"),
                        parse_int(required_option(args, "--hours-used"), "--hours-used"),
                        parse_int(required_option(args, "--hour-limit"), "--hour-limit")};
            validate_asset(asset);
            if (std::any_of(assets.begin(), assets.end(), [&](const Asset& existing) {return existing.id == asset.id;}))
                throw std::runtime_error("Asset id already exists: " + asset.id);
            assets.push_back(asset);
            save_assets(input_file, assets);
            std::cout << "Added asset " << asset.id << '\n';
        } else if (command == "service") {
            if (args.empty() || args[0].rfind("--", 0) == 0)
                throw std::runtime_error("Use: service ASSET_ID --date YYYY-MM-DD");
            const auto date = required_option(args, "--date");
            parse_date(date);
            auto it = std::find_if(assets.begin(), assets.end(), [&](const Asset& a){ return a.id == args[0]; });
            if (it == assets.end()) throw std::runtime_error("Unknown asset id: " + args[0]);
            if (days_from_civil(parse_date(date)) < days_from_civil(parse_date(it->last_serviced)))
                throw std::runtime_error("New service date cannot precede previous service date");
            it->last_serviced = date;
            it->hours_since_service = 0;
            save_assets(input_file, assets);
            std::cout << "Updated maintenance record for " << it->id << '\n';
        } else {
            throw std::runtime_error("Unknown command: " + command + " (use --help)");
        }
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << '\n';
        return 1;
    }
}
