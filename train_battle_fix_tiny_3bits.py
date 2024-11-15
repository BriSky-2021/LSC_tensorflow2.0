"""Self Play
"""

import argparse
import os
import tensorflow as tf
import numpy as np
import magent
import pdb
from examples.battle_model.algo import spawn_ai
from examples.battle_model.algo import tools
from examples.battle_model.senario_battle import play
# from tensorflow import set_random_seed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config(size):
    gw = magent.gridworld
    cfg = gw.Config()

    cfg.set({"map_width": size, "map_height": size})
    cfg.set({"minimap_mode": False})
    cfg.set({"embedding_size": 10})

    small = cfg.register_agent_type(
        "small",
        {'width': 1, 'length': 1, 'hp': 10, 'speed': 2,
         'view_range': gw.CircleRange(6), 'attack_range': gw.CircleRange(1.5),
         'damage': 2, 'step_recover': 0.1,

         'step_reward': -0.005,  'kill_reward': 5, 'dead_penalty': -0.1, 'attack_penalty': -0.1,
         })
    tiny = cfg.register_agent_type(
        "tiny",
        {'width': 1, 'length': 1, 'hp': 4, 'speed':1,
         'view_range': gw.CircleRange(6), 'attack_range': gw.CircleRange(1.5),
         'damage': 1, 'step_recover': 0.2,

         'step_reward': 0,  'kill_reward': 0, 'dead_penalty': -2, 'attack_penalty': -0.01,
         })

 
    g0 = cfg.add_group(tiny)
    g1 = cfg.add_group(small)

    a = gw.AgentSymbol(g0, index='any')
    b = gw.AgentSymbol(g1, index='any')

    # reward shaping to encourage attack
    cfg.add_reward_rule(gw.Event(a, 'attack', b), receiver=a, value=5)
    cfg.add_reward_rule(gw.Event(b, 'attack', a), receiver=b, value=0.2)

    return cfg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--algo', type=str, choices={'ac', 'mfac', 'mfq', 'il','mfqc','ilqc','milc','millc','mill','cil','hil','gil','atoc'}, help='choose an algorithm from the preset', required=True)
    parser.add_argument('--save_every', type=int, default=10, help='decide the self-play update interval')
    parser.add_argument('--update_every', type=int, default=5, help='decide the udpate interval for q-learning, optional')
    parser.add_argument('--n_round', type=int, default=2000, help='set the trainning round')
    parser.add_argument('--render', action='store_true', help='render or not (if true, will render every save)')
    parser.add_argument('--map_size', type=int, default=40, help='set the size of map')  # then the amount of agents is 64
    parser.add_argument('--max_steps', type=int, default=400, help='set the max steps')
    parser.add_argument('--len_nei',type=int,default=40)
    parser.add_argument('--rewardtype',type=str, choices={'self','all','adv','ch'},default='self')
    parser.add_argument('--crp',type=str,default='None')
    parser.add_argument('--usemsg',type=str,default='None')
    parser.add_argument('--idx', type=str, default='6-1995selfnomnw')
    parser.add_argument('--seed',type=int,default=1234)

    args = parser.parse_args()

    np.random.seed(args.seed)
    # set_random_seed(args.seed)
    tf.random.set_seed(args.seed)
    # Initialize the environment
    # env = magent.GridWorld('battle', map_size=args.map_size)
    env=magent.GridWorld(load_config(size=args.map_size))
    # cfg.set({"minimap_mode": True})
    env.set_render_dir(os.path.join(BASE_DIR, 'examples/battle_model', 'build/render'))
    handles = env.get_handles()


    # 禁用 Eager Execution（如果你使用 TensorFlow 1.x 的代码）
    tf.compat.v1.disable_eager_execution()
    # 使用 ConfigProto 配置
    tf_config = tf.compat.v1.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    #tf_config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    tf_config.gpu_options.allow_growth = True

    log_dir = os.path.join(BASE_DIR,'data/tmp/{}'.format(args.algo+'fixtiny3b6h'+str(args.seed)+'-'+str(args.len_nei)))
    model_dir = os.path.join(BASE_DIR, 'data/models/{}'.format(args.algo+'fixtiny256a6h'+str(args.seed)+'-'+str(args.len_nei)))

    if args.algo in ['mfq', 'mfac']:
        use_mf = True
    else:
        use_mf = False 

    start_from = 0
    # pdb.set_trace()
    # print('aa')
    # print(args.crp)


    # 替换 tf.Session 为 tf.compat.v1.Session
    sess = tf.compat.v1.Session(config=tf_config)
    #sess = tf.Session(config=tf_config)
    main_model_dir = os.path.join(BASE_DIR, 'data/models/{}-0'.format(args.algo+'fixtiny64a6h'+str(args.seed)+'-'+str(args.len_nei)))


    oppo_model_dir = os.path.join(BASE_DIR, 'data/models/{}-1'.format('il'))
    main_msg_dir = os.path.join(BASE_DIR, 'data/models/{}-msg0'.format(args.algo+'fixtiny64a6h'+str(args.seed)+'-'+str(args.len_nei)))
    oppo_msg_dir = os.path.join(BASE_DIR, 'data/models/{}-msg1'.format(args.algo))


    models = [spawn_ai(args.algo, sess, env, handles[0], args.algo + '-me', args.max_steps,args.len_nei), spawn_ai('il',sess, env, handles[1],'il-oppo', args.max_steps,args.len_nei)]
    
    # models = [spawn_ai(args.algo, sess, env, handles[0], args.algo + '-me', args.max_steps), spawn_ai(args.algo, sess, env, handles[1],  args.algo+'-oppo', args.max_steps)]
    
    if args.usemsg!='None':
        MsgModels = [spawn_ai('msgdqn', sess, env, handles[0], 'msgdqn'+ '-me', args.max_steps), spawn_ai('msgdqn', sess, env, handles[1], 'msgdqn' + '-opponent', args.max_steps)]
    else:
        print('do not use msg models')
        MsgModels=[None,None]
    # 替换
    sess.run(tf.compat.v1.global_variables_initializer())
    #sess.run(tf.global_variables_initializer())

    if args.idx!='None':
    #    models[0].load(main_model_dir, step=args.idx)
        print('load successfully'+str(args.idx))
#        pdb.set_trace()
        models[1].load(oppo_model_dir, step=args.idx)

#    if args.usemsg!='None':
        
#        models[0].load(main_model_dir,step='6-0selfcrpw')
#        MsgModels[0].load(main_msg_dir,step='6-0selfcrpw')
#    else:
#        models[0].load(main_model_dir,step='6-0selfnomnw')
    if args.crp!='None':
        crp=True
    else:
        crp=False
    runner = tools.Runner(sess, env, handles, args.map_size, args.max_steps, models,MsgModels ,play,
                            render_every=args.save_every if args.render else 0, save_every=args.save_every, tau=0.01, log_name=args.algo,
                            log_dir=log_dir, model_dir=model_dir, train=True,len_nei=args.len_nei,rewardtype= args.rewardtype,crp=crp,is_selfplay=False,is_fix=True)

#    start_from=2000
    for k in range(start_from, start_from + args.n_round):
        eps = magent.utility.piecewise_decay(k, [0, 700,1400, 2000], [1, 0.3,0.01,0.01])
        # eps=0   
        runner.run(eps, k)
