const minimist = require('minimist');
const { login } = require("tplink-cloud-api");
const uuidV4 = require("uuid/v4");

const TPLINK_USER = process.env.TPLINK_USER;
const TPLINK_PASS = process.env.TPLINK_PASS;
const TPLINK_TERM = process.env.TPLINK_TERM || uuidV4();

async function main() {
  var args = minimist(process.argv.slice(2));

  // Check args
  var username;
  if ('username' in args) {
	  username = args.username;
  } else if (TPLINK_USER) {
	  username = TPLINK_USER;
  } else {
	  console.error("Missing username. You can either set the user name to the environment variable TPLINK_USER or pass it via --username parameter");
	  process.exit(1)
  }

  var password;
  if ('password' in args) {
	  password = args.password;
  } else if (TPLINK_PASS) {
	  password = TPLINK_PASS;
  } else {
	  console.error("Missing password. You can either set the user name to the environment variable TPLINK_PASS or pass it via --password parameter");
	  process.exit(1)
  }

  if (!'toggle' in args) {
	  console.error("Missing required parameter: --toggle");
	  process.exit(1)
  }

  if (!'dev' in args) {
	  console.error("Missing required parameter: --dev");
	  process.exit(1)
  }

  // log in to cloud, return a connected tplink object
  const tplink = await login(username, password, TPLINK_TERM);

  let deviceList = await tplink.getDeviceList();

  console.log("Controlling", args.dev);
  if (args.toggle==='on' || args.toggle===1)
    await tplink.getHS110(args.dev).powerOn();
  else if (args.toggle === 'off' || args.toggle===0)
	  await tplink.getHS110(args.dev).powerOff();
}

main();