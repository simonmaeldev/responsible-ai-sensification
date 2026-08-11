#include <ossia-cpp/ossia-cpp98.hpp>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace {

using NodeMap = std::map<std::string, opp::node>;

std::string decode_base64(const std::string& encoded)
{
  static const std::string alphabet =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string decoded;
  std::uint32_t accumulator = 0;
  int bits = 0;
  for (const unsigned char character : encoded) {
    if (std::isspace(character))
      continue;
    if (character == '=')
      break;
    const auto position = alphabet.find(static_cast<char>(character));
    if (position == std::string::npos)
      throw std::runtime_error("invalid base64 payload");
    accumulator = (accumulator << 6) | static_cast<std::uint32_t>(position);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      decoded.push_back(static_cast<char>((accumulator >> bits) & 0xffu));
      accumulator &= bits == 0 ? 0u : ((1u << bits) - 1u);
    }
  }
  return decoded;
}

void describe(opp::node& node, const std::string& description)
{
  node.set_access(opp::Get);
  node.set_description(description);
}

void add_string(NodeMap& nodes, opp::node& parent, const std::string& name,
                const std::string& path, const std::string& description)
{
  auto node = parent.create_string(name);
  describe(node, description);
  node.set_value(opp::value(""));
  nodes.emplace(path, node);
}

void add_int(NodeMap& nodes, opp::node& parent, const std::string& name,
             const std::string& path, const std::string& description,
             int initial = 0)
{
  auto node = parent.create_int(name);
  describe(node, description);
  node.set_value(opp::value(initial));
  nodes.emplace(path, node);
}

void add_float(NodeMap& nodes, opp::node& parent, const std::string& name,
               const std::string& path, const std::string& description)
{
  auto node = parent.create_float(name);
  describe(node, description);
  node.set_value(opp::value(0.f));
  nodes.emplace(path, node);
}

void add_bool(NodeMap& nodes, opp::node& parent, const std::string& name,
              const std::string& path, const std::string& description)
{
  auto node = parent.create_bool(name);
  describe(node, description);
  node.set_value(opp::value(false));
  nodes.emplace(path, node);
}

NodeMap build_namespace(opp::oscquery_server& server)
{
  NodeMap nodes;
  auto root = server.get_root_node();
  auto rai = root.create_child("rai");
  auto model = rai.create_child("model");
  auto run = rai.create_child("run");
  auto probes = rai.create_child("probes");

  add_string(nodes, model, "name", "/rai/model/name",
             "Loaded model identifier reported by the Emitter.");
  add_string(nodes, run, "id", "/rai/run/id",
             "Unique Emitter generation run identifier.");
  auto token = run.create_child("token");
  add_int(nodes, token, "index", "/rai/run/token/index",
          "One-based generated-token sequence.");
  add_string(nodes, token, "text", "/rai/run/token/text",
             "Exact generated token, including whitespace.");

  for (int slot = 1; slot <= 8; ++slot) {
    const auto number = std::to_string(slot);
    auto probe = probes.create_child(number);
    const auto prefix = "/rai/probes/" + number;
    add_bool(nodes, probe, "enabled", prefix + "/enabled",
             "Whether this stable rack slot carries a published observation.");
    add_string(nodes, probe, "id", prefix + "/id", "Emitter probe identifier.");
    add_string(nodes, probe, "site", prefix + "/site",
               "Real hook site: residual_post, attention_output, mlp_output, or sae.");
    add_int(nodes, probe, "layer", prefix + "/layer",
            "Actual decoder or trained SAE layer.", -1);
    add_string(nodes, probe, "module_path", prefix + "/module_path",
               "Runtime module path that produced this observation.");
    add_string(nodes, probe, "shape", prefix + "/shape",
               "Local tensor or sparse-space shape. Raw values remain local.");
    add_float(nodes, probe, "rms", prefix + "/rms",
              "Root-mean-square tensor activation where meaningful.");
    add_float(nodes, probe, "max_abs", prefix + "/max_abs",
              "Maximum absolute tensor or SAE activation.");
    add_float(nodes, probe, "mean", prefix + "/mean",
              "Arithmetic mean tensor activation or mean active SAE activation.");
    add_int(nodes, probe, "active_count", prefix + "/active_count",
            "Active sparse coordinates; zero for dense tensor probes.");
    add_int(nodes, probe, "top_index", prefix + "/top_index",
            "Strongest sparse feature index; -1 for dense probes.", -1);
    add_float(nodes, probe, "top_activation", prefix + "/top_activation",
              "Strongest sparse feature activation.");
    add_int(nodes, probe, "sequence", prefix + "/sequence",
            "Token sequence at which this slot was last updated.");
  }
  return nodes;
}

void apply_command(NodeMap& nodes, const std::string& line)
{
  const auto first = line.find('\t');
  const auto second = first == std::string::npos ? first : line.find('\t', first + 1);
  if (first == std::string::npos || second == std::string::npos || first != 1)
    throw std::runtime_error("malformed bridge command");
  const char kind = line[0];
  const std::string path = line.substr(first + 1, second - first - 1);
  const std::string payload = line.substr(second + 1);
  auto found = nodes.find(path);
  if (found == nodes.end())
    throw std::runtime_error("unknown OSCQuery path: " + path);

  switch (kind) {
    case 's': found->second.set_value(opp::value(decode_base64(payload))); break;
    case 'i': found->second.set_value(opp::value(std::stoi(payload))); break;
    case 'f': found->second.set_value(opp::value(std::stof(payload))); break;
    case 'b': found->second.set_value(opp::value(payload == "1")); break;
    default: throw std::runtime_error("unknown bridge value type");
  }
}

int argument_port(int argc, char** argv, const std::string& option, int fallback)
{
  for (int index = 1; index + 1 < argc; ++index) {
    if (argv[index] == option)
      return std::stoi(argv[index + 1]);
  }
  return fallback;
}

} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc > 1 && std::string(argv[1]) == "--version") {
      std::cout << "rai-ossia-probe-server 1" << std::endl;
      return 0;
    }
    const int osc_port = argument_port(argc, argv, "--osc-port", 9010);
    const int query_port = argument_port(argc, argv, "--query-port", 5678);
    opp::oscquery_server server("RAI Emitter", osc_port, query_port);
    server.set_echo(false);
    auto nodes = build_namespace(server);
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.empty())
        continue;
      try {
        apply_command(nodes, line);
      } catch (const std::exception& error) {
        std::cerr << "bridge command rejected: " << error.what() << std::endl;
      }
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "libossia probe server failed: " << error.what() << std::endl;
    return 1;
  }
}
