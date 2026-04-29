#!/bin/bash
set -e

nodes=(mongo-rrv-primary mongo-rrv-secondary-1 mongo-rrv-secondary-2)
for node in "${nodes[@]}"; do
  echo "Waiting for $node..."
  until mongosh --host "$node" --eval 'db.runCommand({ ping: 1 })' >/dev/null 2>&1; do
    sleep 1
  done
done

echo "Initializing MongoDB replica set..."
cat > /tmp/init_rs.js <<'EOF'
cfg = {
  _id: "rs0",
  members: [
    {_id: 0, host: "mongo-rrv-primary:27017"},
    {_id: 1, host: "mongo-rrv-secondary-1:27017"},
    {_id: 2, host: "mongo-rrv-secondary-2:27017"}
  ]
};
try {
  rs.initiate(cfg);
} catch (e) {
  printjson(e);
}
printjson(rs.status());
EOF

mongosh --host mongo-rrv-primary /tmp/init_rs.js
